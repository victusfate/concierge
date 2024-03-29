import os

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

from concierge import constants
import time
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics
import redis

log.set_service_name('concierge.welco.me')

config = constants.CONFIG

ENV = constants.ENVIRONMENT
AWS_BUCKET = constants.AWS_BUCKET

s3 = constants.s3
service_name = 'concierge.concierge_queue'

alert_webhook = constants.CONFIG['slack']['webhooks']['es_reporter']

class ConciergeQueue:
  def __init__(self,name,message_queue,ratings_file):
    self.name = name
    self.message_queue = message_queue
    self.ratings_file = ratings_file

  def fetch_data(self,data_path):
    cmd_clean_ratings = 'rm ' + self.ratings_file
    os.system(cmd_clean_ratings)
    s3.get(data_path,self.ratings_file,3)

  def train(self,job_data):
    oNewLogger = Logger(
          LoggerOptions(
              service=service_name, # The App Name for Syslog
              console= True,        # we log to console here
              syslog=False,         # we don't log to syslog here
          )
      )
    log.set_logger(oNewLogger)
    try:
      s3_path     = job_data['s3_path']
      date        = job_data['date']
      timestamp   = job_data['timestamp']
      thread_hash = job_data['--t'] if '--t' in job_data else None
      parent_hash = job_data['--p'] if '--p' in job_data else None
      oNewLogger = Logger(
            LoggerOptions(
                service=service_name, # The App Name for Syslog
                console= True,        # we log to console here
                syslog=False,         # we don't log to syslog here
                thread_hash=thread_hash,
                parent_hash=parent_hash
            )
        )
      log.set_logger(oNewLogger)

      self.fetch_data(s3_path)
      df = data_io.load_dataset(',',self.ratings_file)
      max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
      cf = CollaborativeFilter(self.name,CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
      if max_ts is None:
        max_ts = time.time()
      cf.timestamp = max_ts

      learn_start = time.time()
      cf.learn(dataset,max_ts)
      learn_end = time.time()
      log.info(self.name,'tLearn',learn_end-learn_start)

      # ensure its working before uploading to s3/updating latest model
      user_id   = '128x9v1'
      # grab 10 items I have ratings for this
      df_user   = df.loc[df['user_id'] == user_id]
      item_ids = df_user['item_id'].tolist()[0:10]
      log.info(self.name,'user_items',{ 'user_id': user_id, 'item_ids': item_ids})
      scores = cf.predict(user_id,item_ids)
      log.info(self.name,'predictions',scores)
      
      new_model_metric_path = os.path.join('/tmp/',self.name,str(timestamp))
      cf.export_to_s3(file_path=new_model_metric_path,timestamp=timestamp,date_str=date)
      # clear local model files
      os.system('rm -rf ' + new_model_metric_path)

      # handle scores for places
      cf.cache_scores(df)
      
      # handle popularity map for published places
      cf.popularity_map(df)
  
    except Exception as e:
      log.err(self.name,'training.error','unhandled Exception',e)
      

  def poll(self):
    while True:
      oNewLogger = Logger(
            LoggerOptions(
                service=service_name, # The App Name for Syslog
                console= True,        # we log to console here
                syslog=False,         # we don't log to syslog here
            )
        )
      log.set_logger(oNewLogger)
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

        log.info(self.name,'before_message_queue_pop',int(time.time()))
        job_data = self.message_queue.pop()
        log.info(self.name,'received_payload_data',job_data)
        
        # ensure queue is clear (if we backup training, clear queue)
        self.message_queue.purge()
        
        has_type = 'type' in job_data
        is_training = has_type and job_data['type'] == 'train_recommendations'
        has_data = 's3_path' in job_data
        if is_training and has_data:
          self.train(job_data)
      except Exception as e:
        log.err(self.name,'poll','unhandled Exception',e)

