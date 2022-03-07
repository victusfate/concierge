import redis
import pickle
from concierge import constants

METRIC_KEY = 'river_metric'
MODEL_KEY  = 'river_model'

class Model:
  def __init__(self,metric,model):
    self.model = model
    self.metric = metric

def cache_get_metric_and_model():
  cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
  metric = pickle.loads(cache.get(METRIC_KEY))
  model  = pickle.loads(cache.get(MODEL_KEY))
  return Model(metric,model)

def cache_set_metric_and_model(model):
  cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)
  cache.set(METRIC_KEY,pickle.dumps(model.metric))
  cache.set(MODEL_KEY,pickle.dumps(model.model))
