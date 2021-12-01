import os
import sys
import json
import numpy as np
from sys import platform

from rsyslog_cee import log

from bandolier import message_queue
from bandolier import data_tools
from bandolier.s3util import S3

import consul
import requests


log.set_service_name('concierge')
log.reset()



# ==============================================================================
# == Main Thread Data Processing ===============================================
# ==============================================================================

RATINGS_FILE     = '/tmp/placeScores.csv'

ITEM_COLUMN      = 'item_id'
RATING_COLUMN    = 'rating'
CITY_COLUMN      = 'city_id'
HOOD_COLUMN      = 'hood_id'
USER_COLUMN      = 'user_id'
TIMESTAMP_COLUMN = 'timestamp'
HOUR_COLUMN      = 'hour'
DAY_COLUMN       = 'day'

RATING_COLUMNS = [USER_COLUMN, ITEM_COLUMN, RATING_COLUMN, CITY_COLUMN, HOOD_COLUMN, TIMESTAMP_COLUMN, HOUR_COLUMN, DAY_COLUMN]

MAX_RATING = 2


# Keys for data shards
TRAIN_USER_KEY   = "train_{}".format(USER_COLUMN)
TRAIN_ITEM_KEY   = "train_{}".format(ITEM_COLUMN)
TRAIN_CITY_KEY   = "train_{}".format(CITY_COLUMN)
TRAIN_LABEL_KEY  = "train_labels"
MASK_START_INDEX = "mask_start_index"
VALID_POINT_MASK = "valid_point_mask"
EVAL_USER_KEY    = "eval_{}".format(USER_COLUMN)
EVAL_ITEM_KEY    = "eval_{}".format(ITEM_COLUMN)
EVAL_CITY_KEY    = "eval_{}".format(CITY_COLUMN)
TEST_SET_RATIO   = 2 # train with all data

PARAMS_MAP       = 'params_map'
USER_MAP         = 'user_map'
ITEM_MAP         = 'item_map'
CITY_MAP         = 'city_map'
ITEM_CITY_MAP    = 'item_city_map'
CITY_ITEM_MAP    = 'city_item_map'
INVERSE_ITEM_MAP = 'inv_item_map'

USER_DTYPE = np.int32
ITEM_DTYPE = np.int32
CITY_DTYPE = np.int32

MODELS_PATH              = 'concierge/models'
AWS_REGION               = 'us-east-1'
AWS_BUCKET               = 'welcome.local'
AWS_BUCKET_INTERNAL      = None
TRAINING_QUEUE_ROOT_NAME = None
CONFIG                   = {}
AWS_PROFILE              = None
ENVIRONMENT              = 'd2'
REDIS_HOST               = None

training_queue           = None
s3                       = None
CONSUL_HOST              = None

MIN_PLACE_SCORE = -1.0
MAX_PLACE_SCORE =  2.0

def setConfig(env=None):
  global CONSUL_HOST, CONFIG, ENVIRONMENT, TRAINING_QUEUE_ROOT_NAME
  global AWS_REGION, AWS_BUCKET, AWS_BUCKET_INTERNAL, REDIS_HOST
  global AWS_PROFILE, MODELS_PATH
  try:
    CONSUL_HOST = os.getenv('CONSUL_HOST')
    print('CONSUL_HOST',CONSUL_HOST)
    c = consul.Consul(host=CONSUL_HOST)
    consul_url = 'http://' + CONSUL_HOST + ':8500/v1/kv/?keys'
    # print('consul_url',consul_url)
    keys = requests.get(consul_url)
    keys = keys.json()
    # print('keys',keys)
    consul_list = []
    for key in keys:
      consul_tuple = c.kv.get(key,None)
      consul_list.append(consul_tuple[1])
    # print('consul_list',consul_list)
    CONFIG = data_tools.consul_to_nested_dict(consul_list)
    # print('CONFIG',CONFIG)
  except Exception as e:
    print('recommend.constants consul exception',e)

  if not CONFIG and env:
    dirname = os.path.dirname(__file__)
    CONFIG_PATH = os.path.join(dirname, 'bin/config_' +  env + '.json')
    with open(CONFIG_PATH) as config_file:
      CONFIG = json.load(config_file)

  if 'environment' in CONFIG:
    ENVIRONMENT = CONFIG['environment']

  if 'aws' in CONFIG and 'region' in CONFIG['aws']:
    AWS_REGION = CONFIG['aws']['region']

  if 'aws' in CONFIG and 's3' in CONFIG['aws'] and 'buckets' in CONFIG['aws']['s3'] and 'primary' in CONFIG['aws']['s3']['buckets']:
    AWS_BUCKET = CONFIG['aws']['s3']['buckets']['primary']

  if 'aws' in CONFIG and 's3' in CONFIG['aws'] and 'buckets' in CONFIG['aws']['s3'] and 'internal' in CONFIG['aws']['s3']['buckets']:
    AWS_BUCKET_INTERNAL = CONFIG['aws']['s3']['buckets']['internal']

  if 'cache' in  CONFIG and 'redis' in CONFIG['cache'] and 'host' in CONFIG['cache']['redis']:
    REDIS_HOST = CONFIG['cache']['redis']['host']

  if platform == 'darwin':
    AWS_PROFILE = 'welco'

  if sys.platform == 'darwin':
    MODELS_PATH = 'recommender/mac_models'

# setConfig()

# shared s3 interface
print('AWS_BUCKET',AWS_BUCKET,'AWS_REGION',AWS_REGION)
if AWS_BUCKET and AWS_REGION:
  s3 = S3(bucket_name=AWS_BUCKET,profile_name=AWS_PROFILE,region_name=AWS_REGION)

print('s3',s3)

MIN_NUM_RATINGS = 10

# The number of negative examples attached with a positive example
# when performing evaluation.
NUM_EVAL_NEGATIVES = 999

