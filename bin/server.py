from sanic import Sanic
from sanic.response import json as sanic_json
import json
import time
import requests
# import json
from concierge.collaborative_filter import CollaborativeFilter
import redis
import asyncio
import os
import psutil

# import async_timeout
# import aioredis
# import aiohttp

PORT = 5000
CHANNEL = 'cf_updates'

app = Sanic("Concierge")

cache = redis.Redis(host='localhost', port=6379, db=0)   

cf = CollaborativeFilter(None)
tCacheGetStart = time.time()
cf.cache_get_metric_and_model()
tCacheGetEnd = time.time()
print('metric',cf.metric)
print('model',cf.model)
print('tCacheGet',tCacheGetEnd-tCacheGetStart)

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

@app.route('/user/<user_id>/items/<items_str>')
async def user_places(request,user_id=None,items_str=''):
  global cf
  item_ids = items_str.split(',')
  return sanic_json(cf.predict(user_id,item_ids))

async def sub():
  global cf
  await cf.subscribe_to_updates(CHANNEL)

@app.after_server_start
async def after_server_start(app, loop):
    app.add_task(sub())

if __name__ == '__main__':
    app.run(port=PORT)
