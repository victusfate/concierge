import pandas as pd
import time
import os
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics
import redis
import requests
import json
import hashlib

PORT = 5000
cache = redis.Redis(host='localhost', port=6379, db=0)   

# how to generate a diff of two files by row
# comm -2 -3 <(sort /tmp/placeScores.csv) <(sort ~/Desktop/placeScores.csv) > ~/Desktop/deltaScores.csv
df = data_io.load_dataset(',','/Users/messel/Desktop/deltaScores.csv')

ordered_data = {}
now = int(time.time())
for user_item_score in df.itertuples():
  user_id = user_item_score.user_id
  item_id = user_item_score.item_id
  rating  = user_item_score.rating
  # ts      = user_item_score.timestamp
  ts      = now
  event = {'user_id':user_id,'item_id':item_id,'rating':rating,'timestamp':ts}
  sevent = json.dumps(event)
  ordered_data[sevent] = ts
  # event_sha1 = hashlib.sha1(sevent.encode('utf-8')).hexdigest()
  cache_key = 'feed_events'
  # cache.zadd(cache_key,{sevent:ts})  

cache_key = 'feed_events'
cache.zadd(cache_key,ordered_data)
