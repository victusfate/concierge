import pandas as pd
import time
import pickle
from concierge import data_io
from concierge import constants
from river import metrics,stats,compose,facto
from river import meta,optim,reco
from river.evaluate import progressive_val_score
import redis


cache = redis.Redis(host='localhost', port=6379, db=0)   

METRIC_KEY = 'river_metric'
MODEL_KEY  = 'river_model'

MODEL_FILE  = '/tmp/model.sav'
METRIC_FILE = '/tmp/metric.sav'

class CollaborativeFilter:
  def __init__(self,model,metric = metrics.MAE() + metrics.RMSE()):
    self.model   = model
    self.metric  = metric

  def df_to_dataset(df):
    dataset = []
    for user_item_score in df.itertuples():
      user_id = user_item_score.user_id
      item_id = user_item_score.item_id
      rating  = user_item_score.rating
      dataset.append(({'user': user_id,'item': item_id},rating))
    return dataset

  def cache_get_metric_and_model(self):
    metric = pickle.loads(cache.get(METRIC_KEY))
    model  = pickle.loads(cache.get(MODEL_KEY))
    return metric,model

  def cache_set_metric_and_model(self):
    cache.set(METRIC_KEY,pickle.dumps(self.metric))
    cache.set(MODEL_KEY,pickle.dumps(self.model))

  # old file IO
  def save_to_file(self):
    pickle.dump(self.model,open(MODEL_FILE, 'wb'))
    pickle.dump(self.metric,open(METRIC_FILE,'wb'))

  def load_from_file(self):
    self.model  = pickle.load(open(MODEL_FILE, 'rb'))
    self.metric = pickle.load(open(METRIC_FILE, 'rb'))

  # note also modifies the model + metrics
  def evaluate(self,dataset):
      _ = progressive_val_score(dataset,self.model, self.metric, print_every=25_000, show_time=True, show_memory=True)

  def data_stats(dataset):
    mean = stats.Mean()
    for i, x_y in enumerate(dataset, start=1):
        _, y = x_y
        metric.update(y, mean.get())
        mean.update(y)

        if not i % 1_000:
            print(f'[{i:,d}] {metric}')

  def learn(self,dataset):
    for x, y in dataset:
      y_pred = self.model.predict_one(x)      # make a prediction
      self.metric = self.metric.update(y, y_pred)  # update the metric
      self.model = self.model.learn_one(x, y)      # make the model learn 

  #adding to the global running mean two bias terms characterizing the user and the item discrepancy from the general tendency. The model equation is defined as:
  # yhat(x) = ybar + bu_{u} + bi_{i}
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
  # yhat(x) = ybar + bu_{u} + bi_{i} + <v_{u},v_{i}>
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
      'intercept': 3,
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
      score = self.model.predict_one({'user': user_id,'item': item_id})
      scores[item_id] = score
    # sort desc by score
    scores = {k: v for k, v in sorted(scores.items(), key=lambda item: item[1],reverse=True)}  
    return scores

