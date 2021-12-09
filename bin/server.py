from sanic import Sanic
from sanic.response import json as sanic_json
import json
import time
import requests
# import json
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
import redis
import asyncio
import os
import psutil
import threading

# import async_timeout
# import aioredis
# import aiohttp

PORT = 5000
CHANNEL = 'cf_updates'

app = Sanic("Concierge")

cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

cf = CollaborativeFilter(None)
tModelStart = time.time()
cf.import_from_s3()
cf.delta_update()
tModelEnd = time.time()
print('metric',cf.metric)
print('model',cf.model)
print('timestamp',cf.model.timestamp)
print('tModelLoad',tModelEnd-tModelStart)

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
  print('/health',logs)
  return sanic_json(logs)

@app.route('/user/<user_id>/items/<items_str>')
async def user_items(request,user_id=None,items_str=''):
  global cf
  item_ids = items_str.split(',')
  return sanic_json(cf.predict(user_id,item_ids))

async def sub():
  global cf
  await cf.subscribe_to_updates(CHANNEL)

@app.after_server_start
async def after_server_start(app, loop):
  app.add_task(sub())

def training_queue_worker():
  dir_path = os.path.dirname(os.path.realpath(__file__))
  os.system('/usr/bin/python3 ' + os.path.join(dir_path,'concierge_queue_listener.py'))
  
# start queue in seprate thread
queue_thread = threading.Thread(target=training_queue_worker,daemon=True)
queue_thread.start()


if __name__ == '__main__':
  app.run(host='0.0.0.0',port=PORT)
