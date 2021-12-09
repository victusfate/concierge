import os

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

from concierge import constants
import time
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics

log.set_service_name('concierge.welco.me')

config = constants.CONFIG

ENV = constants.ENVIRONMENT
AWS_BUCKET = constants.AWS_BUCKET

s3 = constants.s3
concierge_queue = constants.concierge_queue 

oNewLogger = Logger(
      LoggerOptions(
          service='concierge.training_queue', # The App Name for Syslog
          console= True,        # we log to console here
          syslog=False,         # we don't log to syslog here
      )
  )
log.set_logger(oNewLogger)

alert_webhook = constants.CONFIG['slack']['webhooks']['es_reporter']

def fetch_data(data_path):
  cmd_clean_ratings = 'rm ' + constants.RATINGS_FILE
  os.system(cmd_clean_ratings)
  s3.get(data_path,constants.RATINGS_FILE,3)

def train(job_data):
  try:
    s3_path     = job_data['s3_path']
    date        = job_data['date']
    timestamp   = job_data['timestamp']
    thread_hash = job_data['--t'] if '--t' in job_data else None
    parent_hash = job_data['--p'] if '--p' in job_data else None
    oNewLogger = Logger(
          LoggerOptions(
              service='concierge.train', # The App Name for Syslog
              console= True,        # we log to console here
              syslog=False,         # we don't log to syslog here
              thread_hash=thread_hash,
              parent_hash=parent_hash
          )
      )
    log.set_logger(oNewLogger)

    fetch_data(s3_path)
    df = data_io.load_dataset(',',constants.RATINGS_FILE)
    max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
    cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
    cf.timestamp = max_ts

    tLearnStart = time.time()
    cf.learn(dataset,max_ts)
    tLearnEnd = time.time()
    log.info('tLearn',tLearnEnd-tLearnStart)

    # ensure its working before uploading to s3/updating latest model
    user_id   = '128x9v1'
    # grab 10 feed events I have ratings for this
    df_user   = df.loc[df['user_id'] == user_id]
    item_ids = df_user['item_id'].tolist()
    log.info({ 'user_id': user_id, 'item_ids': item_ids})
    scores = cf.predict(user_id,item_ids)
    log.info('predictions',scores)
    
    new_model_metric_path = '/tmp/' + str(timestamp)
    cf.export_to_s3(file_path=new_model_metric_path,date_str=date,timestamp=timestamp)
    # clear local model files
    os.system('rm -rf ' + new_model_metric_path)
    
  except Exception as e:
    log.err('train unhandled Exception',e)

def concierge_queue_listener(concierge_queue):
  while True:
    try:
      # sample payload
      # {
      #   'type': 'train_feed_recommendations',
      #   's3_path': 's3://d2.welco.me/concierge/event_scores/2020-01-28/1580237292_eventScores.csv',
      #   'date': '2020-02-27',
      #   'timestamp': 1582839506,
      #   '--t': 'thread_hash',
      #   '--p': 'parent_hash'
      # }

      log.info('before concierge queue pop',int(time.time()))
      job_data = concierge_queue.pop()
      log.info('received payload data',job_data)
      
      # ensure queue is clear (if we backup training, clear queue)
      concierge_queue.purge()
      
      has_type = 'type' in job_data
      is_training = has_type and job_data['type'] == 'train_feed_recommendations'
      has_data = 's3_path' in job_data
      if is_training and has_data:
        train(job_data)
    except Exception as e:
      log.err('concierge_queue_listener unhandled Exception',e)

concierge_queue_listener(concierge_queue)