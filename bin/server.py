from sanic import Sanic
from sanic.response import json as sanic_json
import json
import time
import requests
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
import redis
import asyncio
import os
import psutil

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

PORT = 5000

tStart = time.time()

app = Sanic("Concierge")
cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

def reset_logger():
  oNewLogger = Logger(
        LoggerOptions(
            service='concierge.welco.me', # The App Name for Syslog
            console= True,        # we log to console here
            syslog=  False        # Output logs to syslog
        )
    )
  log.set_logger(oNewLogger)
reset_logger()
log.info('deployment bump start',tStart)

def load_cf_model(name: str):
  cf_model = CollaborativeFilter(name)
  tModelStart = time.time()
  cf_model.import_from_s3()
  cf_model.delta_update()
  tModelEnd = time.time()
  log.info(cf_model.name,'metrics',cf_model.metric)
  log.info(cf_model.name,'model',cf_model.model)
  log.info(cf_model.name,'timestamp',cf_model.model.timestamp)
  log.info(cf_model.name,'tModelLoad',tModelEnd-tModelStart)
  cf_model.model.random_items = cf_model.random_items(30)
  log.info(cf_model.name,'random items(useful for testing)',','.join(cf_model.model.random_items))
  return cf_model

cf_events = load_cf_model(constants.CF_EVENT)
cf_media  = load_cf_model(constants.CF_MEDIA)
cf_places = load_cf_model(constants.CF_PLACE)
cf_tags   = load_cf_model(constants.CF_TAG)

@app.route('/')
async def index(request):
  return sanic_json({'message': 'yup'})

@app.route('/health')
async def health(request):    
  pid = os.getpid()
  process = psutil.Process(pid)
  memory_bytes = process.memory_info().rss  # in bytes 
  logs = {
    'service': 'Concierge',
    'purpose': 'Concierge',
    'process': pid,
    'memory': memory_bytes 
  }
  return sanic_json(logs)

@app.route('/user/<user_id>/events/<items_str>',methods=['GET'])
async def user_events_get(request,user_id=None,items_str=''):
  global cf_events
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_get',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_events_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/events',methods=['POST'])
async def user_events_post(request,user_id=None):
  global cf_events
  reset_logger()
  item_ids = request.json.get('events')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_post',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_events_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/media/<items_str>',methods=['GET'])
async def user_media_get(request,user_id=None,items_str=''):
  global cf_media
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_get',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_media_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/media',methods=['POST'])
async def user_media_post(request,user_id=None):
  global cf_media
  reset_logger()
  item_ids = request.json.get('media')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_post',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_media_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/places/<items_str>',methods=['GET'])
async def user_places_get(request,user_id=None,items_str=''):
  global cf_places
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_places.predict(user_id,item_ids)
  log.info(cf_places.name,'user_places_get',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_places_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/places',methods=['POST'])
async def user_places_post(request,user_id=None):
  global cf_places
  reset_logger()
  item_ids = request.json.get('places')
  results = cf_places.predict(user_id,item_ids)
  log.info(cf_places.name,'user_places_post',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_places_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/tags',methods=['GET'])
@app.route('/user/<user_id>/tags/<items_str>',methods=['GET'])
async def user_tags_get(request,user_id=None,items_str=''):
  global cf_tags
  reset_logger()

  if items_str == '':
    item_ids = cf_tags.get_items()
  else:
    item_ids = items_str.split(',')

  results = {}
  results = cf_tags.predict(user_id,item_ids)
  log.info(cf_tags.name,'user_tags_get',{'user_id': user_id, 'ymin': cf_tags.model.y_min, 'ymax': cf_tags.model.y_max, 'results': results})
  log.oLogger.summary('server.user_tags_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/tags',methods=['POST'])
async def user_tags_post(request,user_id=None):
  global cf_tags
  reset_logger()
  item_ids = request.json.get('tags')
  results = cf_tags.predict(user_id,item_ids)
  log.info(cf_tags.name,'user_tags_post',{'user_id': user_id, 'ymin': cf_tags.model.y_min, 'ymax': cf_tags.model.y_max, 'results': results})
  log.oLogger.summary('server.user_tags_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/rankings/<users_str>',methods=['GET'])
async def user_rankings_get(request,user_id=None,users_str=''):
  global cf_places
  reset_logger()

  user_ids = users_str.split(',')

  results = {}
  results = cf_places.user_rankings(user_id,user_ids)
  log.info(cf_tags.name,'user_rankings_get',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_rankings_get.Summary')
  return sanic_json(results)
  

async def sub():
  global cf_events,cf_media,cf_places,cf_tags
  event_sub_future = cf_events.subscribe_to_updates(constants.EVENTS_CHANNEL)
  media_sub_future = cf_media.subscribe_to_updates(constants.MEDIA_CHANNEL)
  place_sub_future = cf_places.subscribe_to_updates(constants.PLACE_CHANNEL)
  tag_sub_future = cf_events.subscribe_to_updates(constants.TAG_CHANNEL)
  results = await asyncio.gather(event_sub_future,media_sub_future,place_sub_future,tag_sub_future,return_exceptions=True)
  return results

@app.after_server_start
async def after_server_start(app, loop):
  results = await sub()
  for result in results:
    print('result',result)
    if isinstance(result,Exception):
      log.err('after_server_start.exception',result)
      exit(0)
    else:
      log.info('after_server_start.sub',result)

if __name__ == '__main__':
  app.run(host='0.0.0.0',port=PORT)
