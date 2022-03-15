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

cf_events = CollaborativeFilter(constants.CF_EVENT)
tModelStart = time.time()
cf_events.import_from_s3()
cf_events.delta_update()
tModelEnd = time.time()
log.info(cf_events.name,'metrics',cf_events.metric)
log.info(cf_events.name,'model',cf_events.model)
log.info(cf_events.name,'timestamp',cf_events.model.timestamp)
log.info(cf_events.name,'tModelLoad',tModelEnd-tModelStart)
cf_events.model.random_items = cf_events.random_items(30)
log.info(cf_events.name,'random items(useful for testing)',','.join(cf_events.model.random_items))

cf_media = CollaborativeFilter(constants.CF_MEDIA)
tModelStart = time.time()
cf_media.import_from_s3()
cf_media.delta_update()
tModelEnd = time.time()
log.info(cf_media.name,'metrics',cf_media.metric)
log.info(cf_media.name,'model',cf_media.model)
log.info(cf_media.name,'timestamp',cf_media.model.timestamp)
log.info(cf_media.name,'tModelLoad',tModelEnd-tModelStart)
cf_media.model.random_items = cf_media.random_items(30)
log.info(cf_media.name,'random items(useful for testing)',','.join(cf_media.model.random_items))

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

@app.route('/user/<user_id>/items/<items_str>',methods=['GET'])
async def user_items_get(request,user_id=None,items_str=''):
  global cf_events
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_get',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/items',methods=['POST'])
async def user_items_post(request,user_id=None):
  global cf_events
  reset_logger()
  item_ids = request.json.get('items')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_post',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/events/<items_str>',methods=['GET'])
async def user_events_get(request,user_id=None,items_str=''):
  global cf_events
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_get',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/events',methods=['POST'])
async def user_events_post(request,user_id=None):
  global cf_events
  reset_logger()
  item_ids = request.json.get('events')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_post',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_post.Summary')
  return sanic_json(results)

# enable once cf_media is trained
@app.route('/user/<user_id>/media/<items_str>',methods=['GET'])
async def user_media_get(request,user_id=None,items_str=''):
  global cf_media
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_get',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/media',methods=['POST'])
async def user_media_post(request,user_id=None):
  global cf_media
  reset_logger()
  item_ids = request.json.get('media')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_post',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_post.Summary')
  return sanic_json(results)

async def sub():
  global cf_events,cf_media
  event_sub_future = cf_events.subscribe_to_updates(constants.EVENTS_CHANNEL)
  media_sub_future = cf_media.subscribe_to_updates(constants.MEDIA_CHANNEL)
  results = await asyncio.gather(event_sub_future,media_sub_future,return_exceptions=True)
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
