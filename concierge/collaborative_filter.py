import pandas as pd
import time
from datetime import datetime
import json
import os
import pickle
from concierge import data_io
from concierge import constants
from river import metrics,stats,compose,facto
from river import meta,optim,reco
from river.evaluate import progressive_val_score
import redis
import asyncio
import async_timeout
import aioredis
import random

METRIC_KEY = 'river_metric'
MODEL_KEY  = 'river_model'

DEFAULT_PATH = '/tmp'
MODEL_FILE  = 'model.sav'
METRIC_FILE = 'metric.sav'

FEED_UPDATES = 'feed_updates'


class CollaborativeFilter:
  def __init__(self,model,metric = metrics.MAE() + metrics.RMSE()):
    self.channel = None
    self.model   = model
    self.metric  = metric

  def df_to_timestamp_and_dataset(df):
    dataset = []
    max_ts  = None
    for user_item_score in df.itertuples():
      user_id = user_item_score.user_id
      item_id = user_item_score.item_id
      rating  = user_item_score.rating
      ts      = user_item_score.timestamp
      if max_ts is None or ts > max_ts:
        max_ts = ts
      dataset.append(({'user': user_id,'item': item_id},rating))
    return max_ts,dataset

  def cache_get_metric_and_model(self):
    cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
    self.metric = pickle.loads(cache.get(METRIC_KEY))
    self.model  = pickle.loads(cache.get(MODEL_KEY))

  def cache_set_metric_and_model(self):
    cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
    cache.set(METRIC_KEY,pickle.dumps(self.metric))
    cache.set(MODEL_KEY,pickle.dumps(self.model))

  # file IO
  def save_to_file(self,file_path = DEFAULT_PATH):
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    print('creating file_path if it does not exist',file_path)
    os.makedirs(file_path, exist_ok=True)
    print('file_path exists?',os.path.exists(file_path))
    pickle.dump(self.model,open(model_path,'wb'))
    pickle.dump(self.metric,open(metric_path,'wb'))

  def load_from_file(self,file_path = DEFAULT_PATH):
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    self.model  = pickle.load(open(model_path,'rb'))
    self.metric = pickle.load(open(metric_path,'rb'))

  def export_to_s3(self,file_path = DEFAULT_PATH,bucket_path = constants.MODELS_PATH,timestamp = None, date_str = None):
    # if no timestamp is passed in, use the model's timestamp    
    if timestamp is None:
      timestamp = self.timestamp
    # if no date_str is passed in, use the model's timestamp and convert to Y-m-d    
    if date_str is None:
      date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    self.save_to_file(file_path)
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    # concierge/models/y-m-d/{timestamp}/{model/metric}.sav path
    constants.s3.put(model_path,os.path.join(bucket_path,date_str,str(timestamp),MODEL_FILE))
    constants.s3.put(metric_path,os.path.join(bucket_path,date_str,str(timestamp),METRIC_FILE))
    # concierge/models/latest/{model/metric}.sav path
    constants.s3.put(model_path,os.path.join(bucket_path,'latest',MODEL_FILE))
    constants.s3.put(metric_path,os.path.join(bucket_path,'latest',METRIC_FILE))

  def import_from_s3(self,file_path = DEFAULT_PATH,bucket_path = constants.MODELS_PATH):
    s3_model_path  = os.path.join(bucket_path,'latest',MODEL_FILE)
    s3_metric_path = os.path.join(bucket_path,'latest',METRIC_FILE)
    model_path     = os.path.join(file_path,MODEL_FILE)
    metric_path    = os.path.join(file_path,METRIC_FILE)
    # concierge/models/latest/{model/metric}.sav path
    print('s3 paths',s3_model_path,s3_metric_path)
    constants.s3.get(s3_model_path,model_path)
    constants.s3.get(s3_metric_path,metric_path)
    self.load_from_file(file_path)

  def update_model(self,message_data):
    dataset = []
    max_ts = None
    for update in message_data:
      user_id = update['user_id']
      item_id = update['item_id']
      rating  = update['rating']
      ts      = update['timestamp']
      dataset.append(({'user': user_id,'item': item_id},rating))
      if max_ts is None or ts > max_ts:
        max_ts = ts    
    for x, y in dataset:
      y_pred = self.model.predict_one(x)      # make a prediction
      self.metric = self.metric.update(y, y_pred)  # update the metric
      self.model = self.model.learn_one(x, y)      # make the model learn   
    if self.model.timestamp is None or (max_ts is not None and max_ts > self.model.timestamp):
      self.model.timestamp = max_ts
      print('updated model timestamp',self.model.timestamp)
    # extra logging for W2-3228
    user_id = '128x9v1'
    random_items = self.random_items(30)
    scores = self.predict(user_id,random_items)
    test_weights = {}
    for item_id in random_items:
      model_item_id = 'item_' + str(item_id)
      if model_item_id in self.model.regressor.steps['FMRegressor'].weights:
        test_weights[item_id] = self.model.regressor.steps['FMRegressor'].weights[model_item_id]
      else:
        test_weights[item_id] = 'NA'
    print('random scores after update for user',user_id,'scores',scores,'test_weights',test_weights)
    


  def delta_update(self):
    cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
    raw_updates = cache.zrangebyscore(FEED_UPDATES,self.model.timestamp,'inf')
    print('delta_update count',len(raw_updates))
    message_data = []
    for update in raw_updates:
      update = update.decode('utf-8')
      message_data.append(json.loads(update))
    self.update_model(message_data)

  async def subscribe_to_updates(self,channel):
    self.channel = channel
    async def reader(channel: aioredis.client.PubSub):
      while True:
        try:
          async with async_timeout.timeout(1):
            message = await channel.get_message(ignore_subscribe_messages=True)
            if message is not None:
              smessage = message["data"].decode()
              print(f"(Reader) Message Received: {smessage}")
              message_data = json.loads(smessage)
              if not isinstance(message_data, list):
                message_data = [message_data]
              self.update_model(message_data)
            await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
          pass
    redis = await aioredis.from_url('redis://' + constants.REDIS_HOST,port=6379, db=0)
    pubsub = redis.pubsub()
    await pubsub.subscribe(self.channel)
    await asyncio.create_task(reader(pubsub))

  # note also modifies the model + metrics
  def evaluate(self,dataset,max_ts):
      _ = progressive_val_score(dataset,self.model, self.metric, print_every=25_000, show_time=True, show_memory=True)
      self.model.timestamp = max_ts

  def learn(self,dataset,max_ts):
    for x, y in dataset:
      y_pred = self.model.predict_one(x)      # make a prediction
      self.metric = self.metric.update(y, y_pred)  # update the metric
      self.model = self.model.learn_one(x, y)      # make the model learn
    self.model.timestamp = max_ts

  # adding to the global running mean two bias terms characterizing the user and 
  # the item discrepancy from the general tendency. 
  # The model equation is defined as:
  #   yhat(x) = ybar + bu_{u} + bi_{i}
  def baseline_model():
    baseline_params = {
      'optimizer': optim.SGD(0.025),
      'l2': 0.,
      'initializer': optim.initializers.Zeros()
    }
    model = meta.PredClipper(
      regressor=reco.Baseline(**baseline_params),
      y_min=constants.MIN_PLACE_SCORE,
      y_max=constants.MAX_PLACE_SCORE
    )
    return model

  # biased matrix factorization, funk svd combination of baseline + funkmf
  #   yhat(x) = ybar + bu_{u} + bi_{i} + <v_{u},v_{i}>
  def bmf_model():
    biased_mf_params = {
      'n_factors': 10,
      'bias_optimizer': optim.SGD(0.025),
      'latent_optimizer': optim.SGD(0.05),
      'weight_initializer': optim.initializers.Zeros(),
      'latent_initializer': optim.initializers.Normal(mu=0., sigma=0.1, seed=73),
      'l2_bias': 0.,
      'l2_latent': 0.
    }
    model = meta.PredClipper(
      regressor=reco.BiasedMF(**biased_mf_params),
      y_min=constants.MIN_PLACE_SCORE,
      y_max=constants.MAX_PLACE_SCORE
    )
    return model

  # https://riverml.xyz/latest/examples/matrix-factorization-for-recommender-systems-part-2/
  #     yhat(x) = w0 + sumj=1->p(wjxj) + sumj=1->p(sumj'=j+1->p(<vj,vj'>xjxj'))
  #     <vj,vj'> = sumf=1->k(vj,f dot vj',f) (dot product of the latent factor vectors)
  def fm_model():
    fm_params = {
      'n_factors': 10,
      'weight_optimizer': optim.SGD(0.025),
      'latent_optimizer': optim.SGD(0.05),
      'sample_normalization': False,
      'l1_weight': 0.,
      'l2_weight': 0.,
      'l1_latent': 0.,
      'l2_latent': 0.,
      'intercept': 1, # mean of scoring
      'intercept_lr': .01,
      'weight_initializer': optim.initializers.Zeros(),
      'latent_initializer': optim.initializers.Normal(mu=0., sigma=0.1, seed=73),
    }

    regressor = compose.Select('user', 'item')
    regressor |= facto.FMRegressor(**fm_params)

    model = meta.PredClipper(
      regressor=regressor,
      y_min=constants.MIN_PLACE_SCORE,
      y_max=constants.MAX_PLACE_SCORE
    )
    return model

  def predict(self,user_id,item_ids):
    scores = {}
    for item_id in item_ids:
      # todo - test check if item is known https://github.com/online-ml/river/discussions/795
      score = 0
      model_item_id = 'item_' + str(item_id)
      if model_item_id in self.model.regressor.steps['FMRegressor'].weights:
        score = self.model.predict_one({'user': user_id,'item': item_id})
      # score = self.model.predict_one({'user': user_id,'item': item_id})
      scores[item_id] = score
    # sort desc by score
    scores = {k: v for k, v in sorted(scores.items(), key=lambda item: item[1],reverse=True)}  
    return scores

  def random_items(self,n=100):
    weights = self.model.regressor.steps['FMRegressor'].weights
    keys = []
    for(k,v) in weights.items():
      akey = k.split('_')
      wtype = akey[0]
      item = akey[1]
      if wtype == 'item':
        keys.append(item)
    return random.sample(keys,n)
