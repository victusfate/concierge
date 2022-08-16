import pandas as pd
import time
import os
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from concierge.concierge_queue import ConciergeQueue
from river import metrics
import redis

cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

df = data_io.load_dataset(',',constants.CF_PUBLISHER)
max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
cf = CollaborativeFilter(constants.CF_PUBLISHER,CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
cf.timestamp = max_ts

# cf.data_stats(dataset)
tLearnStart = time.time()
cf.learn(dataset,max_ts)
# cf.evaluate(dataset)
tLearnEnd = time.time()
print('tLearn',tLearnEnd-tLearnStart)

pq = ConciergeQueue(constants.CF_PUBLISHER,constants.place_queue,constants.PLACE_RATINGS_FILE)
pq.popularity_map(df)

timestamp = int(time.time())
new_model_metric_path = '/tmp/' + str(timestamp)
cf.export_to_s3(new_model_metric_path)
# clear local model files
os.system('rm -rf ' + new_model_metric_path)
os.system('rm /tmp/model.sav')
os.system('rm /tmp/metric.sav')


# make sure it works
load_cf = CollaborativeFilter(constants.CF_PUBLISHER)
tLoadStart = time.time()
load_cf.import_from_s3()
tLoadEnd = time.time()
print('tImport from s3',tLoadEnd-tLoadStart)


print('metric',cf.metric)
print('model',cf.model)

user_id   = '128x9v1'
# grab 10 feed places I have ratings for this
df_user   = df.loc[df['user_id'] == user_id]
item_ids = df_user['item_id'].tolist()
print({ 'user_id': user_id, 'item_ids': item_ids})
scores = cf.predict(user_id,item_ids)
print('predictions',scores)
