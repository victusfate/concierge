from sanic import Sanic
from sanic.response import json as sanic_json
import json
import time
import requests
# import json
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from concierge.training_queue import ConciergeQueue
import redis
import asyncio
import os
import psutil
import threading

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

# import async_timeout
# import aioredis
# import aiohttp

PORT = 5000
CHANNEL = 'cf_updates'

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
log.info('deployment start',tStart)

cf = CollaborativeFilter(None)
tModelStart = time.time()
cf.import_from_s3()
cf.delta_update()
tModelEnd = time.time()
print('metrics',cf.metric)
print('model',cf.model)
print('timestamp',cf.model.timestamp)
print('tModelLoad',tModelEnd-tModelStart)
cf.model.random_items = cf.random_items(30)
print('random items(useful for testing)',','.join(cf.model.random_items))


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
  global cf
  reset_logger()
  item_ids = items_str.split(',')
  results = cf.predict(user_id,item_ids)
  log.info('user_items_get',{'user_id': user_id, 'ymin': cf.model.y_min, 'ymax': cf.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/items',methods=['POST'])
async def user_items_post(request,user_id=None):
  global cf
  reset_logger()
  item_ids = request.json.get('items')
  results = cf.predict(user_id,item_ids)
  log.info('user_items_post',{'user_id': user_id, 'ymin': cf.model.y_min, 'ymax': cf.model.y_max, 'results': results})
  log.oLogger.summary('server.user_items_post.Summary')
  return sanic_json(results)

async def sub():
  global cf
  await cf.subscribe_to_updates(CHANNEL)

@app.after_server_start
async def after_server_start(app, loop):
  app.add_task(sub())

def training_queue_worker():
  cq = ConciergeQueue()
  cq.poll()
  
# start queue in seprate thread
queue_thread = threading.Thread(target=training_queue_worker,daemon=True)
queue_thread.start()


if __name__ == '__main__':
  app.run(host='0.0.0.0',port=PORT)
