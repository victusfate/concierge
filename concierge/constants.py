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

CF_EVENT = 'event'
CF_MEDIA = 'media'
POSSIBLE_CF_NAMES  = [CF_EVENT,CF_MEDIA]
EVENT_RATINGS_FILE = '/tmp/' + CF_EVENT + 'Scores.csv'
MEDIA_RATINGS_FILE = '/tmp/' + CF_MEDIA + 'Scores.csv'
BASE_MODELS_PATH   = 'concierge/'
EVENTS_CHANNEL     = 'cf_' + CF_EVENT + '_updates'
MEDIA_CHANNEL      = 'cf_' + CF_MEDIA + '_updates'
EVENT_UPDATES      = 'event_updates'
MEDIA_UPDATES      = 'media_updates'


ITEM_COLUMN      = 'item_id'
RATING_COLUMN    = 'rating'
USER_COLUMN      = 'user_id'
TIMESTAMP_COLUMN = 'timestamp'

RATING_COLUMNS = [USER_COLUMN, ITEM_COLUMN, RATING_COLUMN, TIMESTAMP_COLUMN]

MAX_RATING = 2


# Keys for data shards
TRAIN_USER_KEY   = "train_{}".format(USER_COLUMN)
TRAIN_ITEM_KEY   = "train_{}".format(ITEM_COLUMN)
TRAIN_LABEL_KEY  = "train_labels"
MASK_START_INDEX = "mask_start_index"
VALID_POINT_MASK = "valid_point_mask"
EVAL_USER_KEY    = "eval_{}".format(USER_COLUMN)
EVAL_ITEM_KEY    = "eval_{}".format(ITEM_COLUMN)
TEST_SET_RATIO   = 2 # train with all data

AWS_REGION               = 'us-east-1'
AWS_BUCKET               = 'welcome.local'
AWS_BUCKET_INTERNAL      = None
EVENT_QUEUE_ROOT_NAME    = None
MEDIA_QUEUE_ROOT_NAME    = None
CONFIG                   = {}
AWS_PROFILE              = None
ENVIRONMENT              = 'd2'
REDIS_HOST               = None

event_queue              = None
media_queue              = None
s3                       = None
CONSUL_HOST              = None

MIN_PLACE_SCORE = -1.0
MAX_PLACE_SCORE =  6.0

def setConfig(env=None):
  global CONSUL_HOST, CONFIG, ENVIRONMENT
  global EVENT_QUEUE_ROOT_NAME, MEDIA_QUEUE_ROOT_NAME
  global AWS_REGION, AWS_BUCKET, AWS_BUCKET_INTERNAL, REDIS_HOST
  global AWS_PROFILE, EVENT_MODELS_PATH, MEDIA_MODELS_PATH
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
    print('concierge.constants consul exception',e)

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

  if 'aws' in CONFIG and 'sqs' in CONFIG['aws'] and 'queues' in CONFIG['aws']['sqs'] and 'event_training' in CONFIG['aws']['sqs']['queues']:
    EVENT_QUEUE_ROOT_NAME = CONFIG['aws']['sqs']['queues']['event_training']

  if 'aws' in CONFIG and 'sqs' in CONFIG['aws'] and 'queues' in CONFIG['aws']['sqs'] and 'media_training' in CONFIG['aws']['sqs']['queues']:
    MEDIA_QUEUE_ROOT_NAME = CONFIG['aws']['sqs']['queues']['media_training']

  def fabio_ip():
    if os.getenv('NOMAD_HOST_IP_concierge'):
      return os.getenv('NOMAD_HOST_IP_concierge')
    if os.getenv('DOMAIN_FABIO'):
      return os.getenv('DOMAIN_FABIO')
    return 'localhost'

  if os.getenv('CACHE_REDIS_HOST'):
    REDIS_HOST = os.getenv('CACHE_REDIS_HOST')
  else:
    REDIS_HOST = fabio_ip()

  print('REDIS_HOST',REDIS_HOST)

  if platform == 'darwin':
    AWS_PROFILE = 'welco'

  if sys.platform == 'darwin':
    EVENT_MODELS_PATH = 'concierge/mac_event_models'
    MEDIA_MODELS_PATH = 'concierge/mac_media_models'

setConfig()

# shared message queues
print('EVENT_QUEUE_ROOT_NAME',EVENT_QUEUE_ROOT_NAME,'ENVIRONMENT',ENVIRONMENT,'AWS_PROFILE',AWS_PROFILE,'AWS_REGION',AWS_REGION)
event_queue = message_queue.MessageQueue(name=EVENT_QUEUE_ROOT_NAME,env=ENVIRONMENT,profile_name=AWS_PROFILE,region_name=AWS_REGION)
media_queue = message_queue.MessageQueue(name=MEDIA_QUEUE_ROOT_NAME,env=ENVIRONMENT,profile_name=AWS_PROFILE,region_name=AWS_REGION)


# shared s3 interface
print('AWS_BUCKET',AWS_BUCKET,'AWS_REGION',AWS_REGION)
if AWS_BUCKET and AWS_REGION:
  s3 = S3(bucket_name=AWS_BUCKET,profile_name=AWS_PROFILE,region_name=AWS_REGION)

print('s3',s3)

MIN_NUM_RATINGS = 10


