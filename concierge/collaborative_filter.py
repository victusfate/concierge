from re import M
import pandas as pd
import time
from datetime import datetime
import json
import os
import pickle
from rsyslog_cee import log
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
import numpy as np
from numpy import dot
from numpy.linalg import norm

DEFAULT_PATH = '/tmp'
MODEL_FILE  = 'model.sav'
METRIC_FILE = 'metric.sav'

def cosine_similarity(x,y):
  x = np.array(x)
  y = np.array(y)
  return dot(x, y)/(norm(x)*norm(y))

def dot_product(x,y):
  x = np.array(x)
  y = np.array(y)
  return dot(x,y)

class CollaborativeFilter:
  def __init__(self,name,model = None,metric = None):
    if (name not in constants.POSSIBLE_CF_NAMES):
      raise ValueError(self.name,'name must be one of: ' + ','.join(constants.POSSIBLE_CF_NAMES))
    self.channel = None
    self.name    = name
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

  # file IO
  def save_to_file(self,file_path):
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    log.info('save_to_file',self.name,'creating file_path if it does not exist',file_path)
    os.makedirs(file_path, exist_ok=True)
    log.info('save_to_file',self.name,'file_path exists?',os.path.exists(file_path))
    pickle.dump(self.model,open(model_path,'wb'))
    pickle.dump(self.metric,open(metric_path,'wb'))

  def load_from_file(self,file_path):
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    self.model  = pickle.load(open(model_path,'rb'))
    self.metric = pickle.load(open(metric_path,'rb'))
    # ensure we always have a valid timestamp for delta training
    if self.model.timestamp is None:
      log.warning('load_from_file',self.name,'model.timestamp is None, setting to now')
      self.model.timestamp = time.time()
    if not hasattr(self.model, 'user_ratings') or self.model.user_ratings is None:
      log.warning('load_from_file',self.name,'user_ratings is None, setting to {}')
      self.model.user_ratings = {}
    
  def get_bucket_path(self,base_bucket_path):
    return os.path.join(base_bucket_path,self.name + '_models')

  def export_to_s3(self,file_path = DEFAULT_PATH,base_bucket_path = constants.BASE_MODELS_PATH,timestamp = None, date_str = None):
    bucket_path = self.get_bucket_path(base_bucket_path)
    # if no timestamp is passed in, use the model's timestamp    
    if timestamp is None:
      timestamp = self.timestamp
    # if no date_str is passed in, use the model's timestamp and convert to Y-m-d    
    if date_str is None:
      date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    self.save_to_file(file_path)
    model_path = os.path.join(file_path,MODEL_FILE)
    metric_path = os.path.join(file_path,METRIC_FILE)
    # concierge/x_models/y-m-d/{timestamp}/{model/metric}.sav path
    constants.s3.put(model_path,os.path.join(bucket_path,date_str,str(timestamp),MODEL_FILE))
    constants.s3.put(metric_path,os.path.join(bucket_path,date_str,str(timestamp),METRIC_FILE))
    # concierge/x_models/latest/{model/metric}.sav path
    constants.s3.put(model_path,os.path.join(bucket_path,'latest',MODEL_FILE))
    constants.s3.put(metric_path,os.path.join(bucket_path,'latest',METRIC_FILE))

  def import_from_s3(self,base_path = DEFAULT_PATH,base_bucket_path = constants.BASE_MODELS_PATH):
    # /tmp/event/{model/metric}.sav
    file_path = os.path.join(base_path,self.name)
    os.makedirs(file_path, exist_ok=True)
    bucket_path    = self.get_bucket_path(base_bucket_path)
    s3_model_path  = os.path.join(bucket_path,'latest',MODEL_FILE)
    s3_metric_path = os.path.join(bucket_path,'latest',METRIC_FILE)
    model_path     = os.path.join(file_path,MODEL_FILE)
    metric_path    = os.path.join(file_path,METRIC_FILE)
    # concierge/models/latest/{model/metric}.sav path
    log.info('import_from_s3',self.name,'s3 paths',s3_model_path,s3_metric_path)
    constants.s3.get(s3_model_path,model_path)
    constants.s3.get(s3_metric_path,metric_path)
    self.load_from_file(file_path)

  def update_model(self,message_data):
    dataset = []
    max_ts = None
    if not hasattr(self.model, 'user_ratings') or self.model.user_ratings is None:
      self.model.user_ratings = {}
      log.warning('update_model',self.name,'user_ratings is None, setting to {}')
    user_ratings = self.model.user_ratings
    log.info('update_model',self.name,'len(user_ratings)',len(user_ratings))
    for update in message_data:
      user_id = update['user_id']
      item_id = update['item_id']
      rating  = update['rating']
      ts      = update['timestamp']
      dataset.append(({'user': user_id,'item': item_id},rating))
      if user_id not in user_ratings:
        user_ratings[user_id] = []
      user_ratings[user_id].append((item_id,rating))      
      if max_ts is None or ts > max_ts:
        max_ts = ts    
    for x, y in dataset:
      y_pred = self.model.predict_one(x)      # make a prediction
      self.metric = self.metric.update(y, y_pred)  # update the metric
      self.model = self.model.learn_one(x, y)      # make the model learn   
    if self.model.timestamp is None or (max_ts is not None and max_ts > self.model.timestamp):
      self.model.timestamp = max_ts
      log.info('update_model',self.name + ' updated model timestamp',self.model.timestamp)
    self.model.user_ratings = user_ratings
    
    # extra logging for W2-3228
    try:
      user_id = '128x9v1'
      random_items = self.model.random_items
      scores = self.predict(user_id,random_items)
      test_weights = {}
      for item_id in random_items:
        model_item_id = 'item_' + str(item_id)
        if model_item_id in self.model.regressor.steps['FMRegressor'].weights:
          test_weights[item_id] = self.model.regressor.steps['FMRegressor'].weights[model_item_id]
        else:
          test_weights[item_id] = 'NA'
      log.info('update_model',self.name,'y_min,y_max',self.model.y_min,self.model.y_max,'random scores after update for user',user_id,'scores',scores,'test_weights',test_weights)
    except Exception as e:
      log.info('update_model',self.name, e)
    


  def delta_update(self):
    set_name = None
    if self.name == constants.CF_EVENT:
      set_name = constants.EVENT_UPDATES
    elif self.name == constants.CF_MEDIA:
      set_name = constants.MEDIA_UPDATES
    elif self.name == constants.CF_PLACE:
      set_name = constants.PLACE_UPDATES
    elif self.name == constants.CF_TAG:
      set_name = constants.TAG_UPDATES
    else:
      return

    log.info('delta_update',self.name,'set_name',set_name,'timestamp',self.model.timestamp)
    cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
    raw_updates = cache.zrangebyscore(set_name,self.model.timestamp,'inf')
    log.info('delta_update',self.name,'count',len(raw_updates))
    message_data = []
    for update in raw_updates:
      update = update.decode('utf-8')
      message_data.append(json.loads(update))
    self.update_model(message_data)

  async def subscribe_to_updates(self,channel):
    try:
      self.channel = channel
      async def reader(channel: aioredis.client.PubSub):
        while True:
          try:
            async with async_timeout.timeout(1):
              message = await channel.get_message(ignore_subscribe_messages=True)
              if message is not None:
                smessage = message["data"].decode()
                log.info('subscribe_to_updates',self.name,f"(Reader) Message Received: {smessage}")
                message_data = json.loads(smessage)
                if not isinstance(message_data, list):
                  message_data = [message_data]
                self.update_model(message_data)
              await asyncio.sleep(0.01)
          except asyncio.TimeoutError:
            pass
      # redis = await aioredis.from_url('redis://thisdoesnotexist',port=6379, db=0)
      redis = await aioredis.from_url('redis://' + constants.REDIS_HOST,port=6379, db=0)
      pubsub = redis.pubsub()
      await pubsub.subscribe(self.channel)
      fut = await asyncio.create_task(reader(pubsub))
      return fut
    except Exception as e:
      log.err('subscribe_to_updates',self.name,e)
      fut = asyncio.get_running_loop().create_future()
      fut.set_exception(e)
      return fut
    
  # note also modifies the model + metrics
  def evaluate(self,dataset,max_ts):
    if not hasattr(self.model, 'user_ratings') or self.model.user_ratings is None:
      log.warning('evaluate',self.name,'user_ratings is None, setting to {}')
      self.model.user_ratings = {}
    user_ratings = self.model.user_ratings
    _ = progressive_val_score(dataset,self.model, self.metric, print_every=25_000, show_time=True, show_memory=True)
    self.model.timestamp = max_ts
    self.model.user_ratings = user_ratings

  def learn(self,dataset,max_ts):
    user_ratings = {}
    for x, y in dataset:
      user_id = x['user']
      item_id = x['item']
      rating  = y
      if user_id not in user_ratings:
        user_ratings[user_id] = []
      user_ratings[user_id].append((item_id,rating))
      y_pred = self.model.predict_one(x)      # make a prediction
      self.metric = self.metric.update(y, y_pred)  # update the metric
      self.model = self.model.learn_one(x, y)      # make the model learn
    self.model.timestamp = max_ts
    self.model.user_ratings = user_ratings


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

  def popularity_map(self,df):
    if self.name != constants.CF_PLACE:
      return
    pr = df.groupby([constants.ITEM_COLUMN])[constants.RATING_COLUMN].sum()
    pr = (pr-pr.min())/(pr.max()-pr.min())
    item_popularity_map = pr.to_dict()
    cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   
    p = cache.pipeline()
    # dump item popularity map into redis
    for k,v in item_popularity_map.items():
      key = constants.PLACE_SCORES_KEY + ':' + k
      p.set(key,v)
    p.execute()


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

  def get_items(self):
    items = []
    model_item_ids = self.model.regressor.steps['FMRegressor'].weights
    for model_item_id in model_item_ids:
      if 'item_' in model_item_id:
        items.append(model_item_id.split('item_')[1])
    return items

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

  # get all ratings for user and compare to other user prediction vectors
  def user_rankings(self,user_id,selected_users):
    similar_users = {}

    user_ratings = []
    if user_id in self.model.user_ratings:
      user_ratings = self.model.user_ratings[user_id]

    # if user_ratings are empty, return random user-user scores    
    if len(user_ratings) == 0:
      for selected_user in selected_users:
        similar_users[selected_user] = random.random()
      similar_users = {k: v for k, v in sorted(similar_users.items(), key=lambda item: item[1],reverse=True)}
      return similar_users
    
    user_scores = {}    
    item_ids = []
    for user_rating in user_ratings:
      item_id = user_rating[0]
      rating  = user_rating[1]
      item_ids.append(item_id)
      user_scores[item_id] = rating

    max_dp = 1
    for selected_user in selected_users:
      su_scores = self.predict(selected_user,item_ids)
      # user ratings, and selected user predicted ratings
      x = []
      y = []
      for item_id in item_ids:
        x.append(user_scores[item_id])
        y.append(su_scores[item_id])
      dist = cosine_similarity(x,y)
      # dist = dot_product(x,y)
      max_dp = max(dist,max_dp)      
      similar_users[selected_user] = dist
    # for selected_user in selected_users:
    #   similar_users[selected_user] = similar_users[selected_user] / max_dp
    similar_users = {k: v for k, v in sorted(similar_users.items(), key=lambda item: item[1],reverse=True)}
    return similar_users

  # faster than user_rankings but lower quality comparison
  def user_rankings2(self,user_id,selected_users):
    user_factor = self.model.regressor.steps['FMRegressor'].latents[user_id]

    similar_users = {}
    max_dp = None
    for selected_user in selected_users:
      su_factor = self.model.regressor.steps['FMRegressor'].latents[selected_user]
      dist = dot(user_factor,su_factor)
      # dist = dot_product(x,y)
      if max_dp is None:
        max_dp = dist
      else:
        max_dp = max(dist,max_dp)      
      similar_users[selected_user] = dist
    if max_dp is None:
      max_dp = 1
    for selected_user in selected_users:
      similar_users[selected_user] = similar_users[selected_user] / max_dp
    similar_users = {k: v for k, v in sorted(similar_users.items(), key=lambda item: item[1],reverse=True)}
    return similar_users

  def random_items(self,n=100):
    weights = self.model.regressor.steps['FMRegressor'].weights
    n = min(n,len(weights))
    if n == 0:
      return []
    keys = []
    for(k,v) in weights.items():
      if 'item_' in k:
        keys.append(k.split('item_')[1])
    if n > len(keys):
      n = len(keys)
    return random.sample(keys,n)
