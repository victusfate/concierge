from sanic import Sanic
from sanic.response import json
import time
# import json
from concierge.collaborative_filter import CollaborativeFilter
import redis
PORT = 5000

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
async def test(request):
    return json({'hello': 'world'})

@app.route('/user/<user_id>/places/<places_str>')
async def user_places(request,user_id=None,places_str=''):
  global cf
  place_ids = places_str.split(',')
  return json(cf.predict(user_id,place_ids))

if __name__ == '__main__':
    app.run(port=PORT)