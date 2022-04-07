import pandas as pd
import time
import os
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics
import redis

cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

# df = data_io.load_dataset(',',constants.PLACE_RATINGS_FILE)
# max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
# tf = CollaborativeFilter(constants.CF_PLACE,CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
# tf.timestamp = max_ts

# # cf.data_stats(dataset)
# tLearnStart = time.time()
# tf.learn(dataset,max_ts)
# # cf.evaluate(dataset)
# tLearnEnd = time.time()
# print('tLearn',tLearnEnd-tLearnStart)

file_path = os.path.join('/tmp/',constants.CF_PLACE)
# tf.save_to_file(file_path)

cf = CollaborativeFilter(constants.CF_PLACE)
cf.load_from_file(file_path)


# similar users
user_id = '128x9v1'
selected_user_ids = [
  '15clr1r',  # Pat
  '1obrasa',  # Mitch
  '12exuzi',  # Peter
  '88i0z7',   # Matthew
  '163hup1',  # Mark A.  
  '15u27fv',  # Marc C.
  'tf40jt',   # Alex	
  '7pungc',   # Rijul
  '1q9v9dh',  # Jake
  '1mkkm8z',  # Kingsley
  'chroyy',   # Fedor
  '1wblyoh',  # Lina
  'ck3th0',   # Wes
  '1jkh13k',  # Ben S.
  'z960qo'    # Igor Golia
]
t1 = time.time()
similarity_scores = cf.user_rankings(user_id,selected_user_ids)
t2 = time.time()
print('similarity',similarity_scores)
print('delta time',t2-t1)