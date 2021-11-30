import json
import requests
import json
import redis
PORT = 5000
CHANNEL = 'cf_updates'
cache = redis.Redis(host='localhost', port=6379, db=0)   

# test real time updates
item_ids = ['gcjsio4c-1qqsc7h','gcjsbtwc-1aep9i6','gcjs8xr8-1xjdfp2','iibwqpe4-1hsmqbr']
ratings  = [-1,2,2,-1]
cache.publish(CHANNEL, json.dumps({'user_id': 'new_user', 'item_id': item_ids[0], 'rating': ratings[0]}))
s1 = requests.get('http://localhost:5000/user/new_user/places/' + ','.join(item_ids))
print('after rating ' + item_ids[0] + ' rating ' + str(ratings[0]),s1.json())
cache.publish(CHANNEL, json.dumps({'user_id': 'new_user', 'item_id': item_ids[1], 'rating': ratings[1]}))
s2 = requests.get('http://localhost:5000/user/new_user/places/' + ','.join(item_ids))
print('after rating ' + item_ids[1] + ' rating ' + str(ratings[1]),s2.json())
cache.publish(CHANNEL, json.dumps({'user_id': 'new_user', 'item_id': item_ids[2], 'rating': ratings[2]}))
s3 = requests.get('http://localhost:5000/user/new_user/places/' + ','.join(item_ids))
print('after rating ' + item_ids[2] + ' rating ' + str(ratings[2]),s3.json())
cache.publish(CHANNEL, json.dumps({'user_id': 'new_user', 'item_id': item_ids[3], 'rating': ratings[3]}))
s4 = requests.get('http://localhost:5000/user/new_user/places/' + ','.join(item_ids))
print('after rating ' + item_ids[3] + ' rating ' + str(ratings[3]),s4.json())

