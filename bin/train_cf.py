import pandas as pd
import time
import os
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics
import redis

cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

df = data_io.load_dataset(',',constants.EVENT_RATINGS_FILE)
max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
cf.timestamp = max_ts

# cf.data_stats(dataset)
tLearnStart = time.time()
cf.learn(dataset,max_ts)
# cf.evaluate(dataset)
tLearnEnd = time.time()
print('tLearn',tLearnEnd-tLearnStart)

# tCacheSetStart = time.time()
# cf.cache_set_metric_and_model()
# tCacheSetEnd = time.time()
# print('tCacheSet',tCacheSetEnd-tCacheSetStart)

# tSaveStart = time.time()
# cf.save_to_file()
# tSaveEnd = time.time()
# print('tSave',tSaveEnd-tSaveStart)

# # make sure it works
# cache_cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
# tCacheGetStart = time.time()
# cache_cf.cache_get_metric_and_model()
# tCacheGetEnd = time.time()
# print('tCacheGet',tCacheGetEnd-tCacheGetStart)

timestamp = int(time.time())
new_model_metric_path = '/tmp/' + str(timestamp)
cf.export_to_s3(new_model_metric_path)
# clear local model files
os.system('rm -rf ' + new_model_metric_path)
os.system('rm /tmp/model.sav')
os.system('rm /tmp/metric.sav')


# make sure it works
# load_cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
load_cf = CollaborativeFilter(None)
tLoadStart = time.time()
load_cf.import_from_s3()
# load_cf.load_from_file()
tLoadEnd = time.time()
print('tImport from s3',tLoadEnd-tLoadStart)


print('metric',cf.metric)
print('model',cf.model)

user_id   = '128x9v1'
# grab 10 feed events I have ratings for this
df_user   = df.loc[df['user_id'] == user_id]
item_ids = df_user['item_id'].tolist()
print({ 'user_id': user_id, 'item_ids': item_ids})
scores = cf.predict(user_id,item_ids)
print('predictions',scores)
