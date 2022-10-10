from sanic import Sanic
from sanic.response import json as sanic_json
import json
import time
import requests
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
import redis
import asyncio
import os
import psutil
import urllib.parse

from os import path
from pathlib import Path

from rsyslog_cee import log
from rsyslog_cee.logger import Logger,LoggerOptions

import spacy
from spacy import displacy

# import pysbd
# sbd_seg = pysbd.Segmenter(language="en", clean=False)

# import en_core_web_trf
# nlp = en_core_web_trf.load()

# nlp = spacy.load('en_core_web_sm')
nlp = spacy.load('en_core_web_trf')

PORT = 5000

tStart = time.time()

app = Sanic("Concierge")
cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

def reset_logger():
  oNewLogger = Logger(
        LoggerOptions(
            service='concierge.welco.me', # The App Name for Syslog
            console= True,        # we log to console here
            syslog=  False        # Output logs to syslog
        )
    )
  log.set_logger(oNewLogger)
reset_logger()
log.info('deployment bump start',tStart)

def load_cf_model(name: str):
  cf_model = CollaborativeFilter(name)
  tModelStart = time.time()
  cf_model.import_from_s3()
  cf_model.delta_update()
  tModelEnd = time.time()
  log.info(cf_model.name,'metrics',cf_model.metric)
  log.info(cf_model.name,'model',cf_model.model)
  log.info(cf_model.name,'timestamp',cf_model.model.timestamp)
  log.info(cf_model.name,'tModelLoad',tModelEnd-tModelStart)
  cf_model.model.random_items = cf_model.random_items(30)
  log.info(cf_model.name,'random items(useful for testing)',','.join(cf_model.model.random_items))
  return cf_model

cf_events = load_cf_model(constants.CF_EVENT)
cf_media  = load_cf_model(constants.CF_MEDIA)
cf_places = load_cf_model(constants.CF_PLACE)
cf_tags   = load_cf_model(constants.CF_TAG)

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

@app.route('/user/<user_id>/events/<items_str>',methods=['GET'])
async def user_events_get(request,user_id=None,items_str=''):
  global cf_events
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_get',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_events_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/events',methods=['POST'])
async def user_events_post(request,user_id=None):
  global cf_events
  reset_logger()
  item_ids = request.json.get('events')
  results = cf_events.predict(user_id,item_ids)
  log.info(cf_events.name,'user_items_post',{'user_id': user_id, 'ymin': cf_events.model.y_min, 'ymax': cf_events.model.y_max, 'results': results})
  log.oLogger.summary('server.user_events_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/media/<items_str>',methods=['GET'])
async def user_media_get(request,user_id=None,items_str=''):
  global cf_media
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_get',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_media_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/media',methods=['POST'])
async def user_media_post(request,user_id=None):
  global cf_media
  reset_logger()
  item_ids = request.json.get('media')
  results = cf_media.predict(user_id,item_ids)
  log.info(cf_media.name,'user_media_post',{'user_id': user_id, 'ymin': cf_media.model.y_min, 'ymax': cf_media.model.y_max, 'results': results})
  log.oLogger.summary('server.user_media_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/places/<items_str>',methods=['GET'])
async def user_places_get(request,user_id=None,items_str=''):
  global cf_places
  reset_logger()
  item_ids = items_str.split(',')
  results = cf_places.predict(user_id,item_ids)
  log.info(cf_places.name,'user_places_get',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_places_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/places',methods=['POST'])
async def user_places_post(request,user_id=None):
  global cf_places
  reset_logger()
  item_ids = request.json.get('places')
  results = cf_places.predict(user_id,item_ids)
  log.info(cf_places.name,'user_places_post',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_places_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/tags',methods=['GET'])
@app.route('/user/<user_id>/tags/<items_str>',methods=['GET'])
async def user_tags_get(request,user_id=None,items_str=''):
  global cf_tags
  reset_logger()

  if items_str == '':
    item_ids = cf_tags.get_items()
  else:
    item_ids = items_str.split(',')

  results = {}
  results = cf_tags.predict(user_id,item_ids)
  log.info(cf_tags.name,'user_tags_get',{'user_id': user_id, 'ymin': cf_tags.model.y_min, 'ymax': cf_tags.model.y_max, 'results': results})
  log.oLogger.summary('server.user_tags_get.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/tags',methods=['POST'])
async def user_tags_post(request,user_id=None):
  global cf_tags
  reset_logger()
  item_ids = request.json.get('tags')
  results = cf_tags.predict(user_id,item_ids)
  log.info(cf_tags.name,'user_tags_post',{'user_id': user_id, 'ymin': cf_tags.model.y_min, 'ymax': cf_tags.model.y_max, 'results': results})
  log.oLogger.summary('server.user_tags_post.Summary')
  return sanic_json(results)

@app.route('/user/<user_id>/rankings/<users_str>',methods=['GET'])
async def user_rankings_get(request,user_id=None,users_str=''):
  global cf_places
  reset_logger()

  user_ids = users_str.split(',')

  results = {}
  results = cf_places.user_rankings(user_id,user_ids)
  log.info(cf_tags.name,'user_rankings_get',{'user_id': user_id, 'ymin': cf_places.model.y_min, 'ymax': cf_places.model.y_max, 'results': results})
  log.oLogger.summary('server.user_rankings_get.Summary')
  return sanic_json(results)

@app.route('/ner/<text>',methods=['GET'])
async def ner_get(request,text=None):
  global nlp
  text = urllib.parse.unquote(text,'utf-8')
  reset_logger()
  doc = nlp(text)
  results = []
  for ent in doc.ents:
    results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
  log.info('ner_get',{'text': text,'results': results})
  log.oLogger.summary('server.ner_get.Summary')
  return sanic_json(results)

@app.route('/ner',methods=['POST'])
async def ner_post(request):
  text = request.json.get('text')
  global nlp
  reset_logger()
  doc = nlp(text)
  results = []
  for ent in doc.ents:
    results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
  log.info('ner_post',{'text': text,'results': results})
  log.oLogger.summary('server.ner_post.Summary')
  return sanic_json(results)

@app.route('/pos/<text>',methods=['GET'])
async def pos_get(request,text=None):
  global nlp
  text = urllib.parse.unquote(text,'utf-8')
  reset_logger()
  doc = nlp(text)
  results = []
  for token in doc:
    results.append({
      'text': token.text,
      'lemma': token.lemma_, 
      'pos': token.pos_, 
      'tag': token.tag_, 
      'dep': token.dep_,
      'shape': token.shape_, 
      'is_alpha': token.is_alpha, 
      'is_stop': token.is_stop 
    })  
  log.info('pos_get',{'text': text,'results': results})
  log.oLogger.summary('server.ner_get.Summary')
  return sanic_json(results)

@app.route('/pos',methods=['POST'])
async def pos_post(request):
  text = request.json.get('text')
  global nlp
  reset_logger()
  doc = nlp(text)
  results = []
  for token in doc:
    results.append({
      'text': token.text,
      'lemma': token.lemma_, 
      'pos': token.pos_, 
      'tag': token.tag_, 
      'dep': token.dep_,
      'shape': token.shape_, 
      'is_alpha': token.is_alpha, 
      'is_stop': token.is_stop 
    })  
  log.info('pos_post',{'text': text,'results': results})
  log.oLogger.summary('server.ner_post.Summary')
  return sanic_json(results)

@app.route('/spacy_seg/<text>',methods=['GET'])
async def spacy_seg_get(request,text=None):
  global nlp
  text = urllib.parse.unquote(text,'utf-8')
  reset_logger()
  doc = nlp(text)
  results = []
  for sentence in doc.sents:
    results.append({
      'text': sentence.text,
      'start': sentence.start_char, 
      'end': sentence.end_char
    })
  log.info('spacy_seg_get',{'text': text,'results': results})
  log.oLogger.summary('server.spacy_seg_get.Summary')
  return sanic_json(results)

@app.route('/spacy_seg',methods=['POST'])
async def spacy_seg_post(request,text=None):
  text = request.json.get('text')
  global nlp
  reset_logger()
  doc = nlp(text)
  results = []
  for sentence in doc.sents:
    results.append({
      'text': sentence.text,
      'start': sentence.start_char, 
      'end': sentence.end_char
    })
  log.info('spacy_seg_post',{'text': text,'results': results})
  log.oLogger.summary('server.spacy_seg_post.Summary')
  return sanic_json(results)

# @app.route('/pysbd_seg/<text>',methods=['GET'])
# async def pysbd_seg_get(request,text=None):
#   global sbd_seg
#   text = urllib.parse.unquote(text,'utf-8')
#   reset_logger()
#   results = sbd_seg.segment(text)
#   log.info('pysbd_seg_get',{'text': text,'results': results})
#   log.oLogger.summary('server.pysbd_seg_get.Summary')
#   return sanic_json(results)

# @app.route('/pysbd_seg',methods=['POST'])
# async def pysbd_seg_post(request,text=None):
#   text = request.json.get('text')
#   global sbd_seg
#   reset_logger()
#   results = sbd_seg.segment(text)
#   log.info('pysbd_seg_post',{'text': text,'results': results})
#   log.oLogger.summary('server.pysbd_seg_post.Summary')
#   return sanic_json(results)

def line_processor(text):
  global nlp
  doc = nlp(text)

  result = {}  
  # segmenter
  segmenter_results = []
  for sentence in doc.sents:
    segmenter_results.append({
      'text': sentence.text,
      'start': sentence.start_char, 
      'end': sentence.end_char
    })
  log.info('line_processor_get',{'text': text,'segmenter_results': segmenter_results})  
  result['segmenter'] = segmenter_results

  # pos
  pos_results = []
  for token in doc:
    pos_results.append({
      'text': token.text,
      'lemma': token.lemma_, 
      'pos': token.pos_, 
      'tag': token.tag_, 
      'dep': token.dep_,
      'shape': token.shape_, 
      'is_alpha': token.is_alpha, 
      'is_stop': token.is_stop 
    })  
  log.info('line_processor_get',{'text': text,'pos_results': pos_results})
  result['pos'] = pos_results

  # ner
  ner_results = []
  for ent in doc.ents:
    ner_results.append({'text': ent.text, 'start_char': ent.start_char, 'end_char': ent.end_char, 'label': ent.label_ })
  log.info('line_processor_get',{'text': text,'ner_results': ner_results})
  result['ner'] = ner_results

  log.oLogger.summary('server.line_processor_get.Summary')
  return result

@app.route('/line_processor/<text>',methods=['GET'])
async def line_processor_get(request,text=None):
  global nlp
  reset_logger()
  text = urllib.parse.unquote(text,'utf-8')
  result = line_processor(text)
  log.oLogger.summary('server.line_processor_get.Summary')
  return sanic_json(result)

@app.route('/line_processor',methods=['POST'])
async def line_processor_post(request,text=None):
  reset_logger()
  global nlp
  text = request.json.get('text')
  result = line_processor(text)
  log.oLogger.summary('server.line_processor_post.Summary')
  return sanic_json(result)



async def sub():
  global cf_events,cf_media,cf_places,cf_tags
  event_sub_future = cf_events.subscribe_to_updates(constants.EVENTS_CHANNEL)
  media_sub_future = cf_media.subscribe_to_updates(constants.MEDIA_CHANNEL)
  place_sub_future = cf_places.subscribe_to_updates(constants.PLACE_CHANNEL)
  tag_sub_future = cf_events.subscribe_to_updates(constants.TAG_CHANNEL)
  results = await asyncio.gather(event_sub_future,media_sub_future,place_sub_future,tag_sub_future,return_exceptions=True)
  return results

@app.after_server_start
async def after_server_start(app, loop):
  results = await sub()
  for result in results:
    print('result',result)
    if isinstance(result,Exception):
      log.err('after_server_start.exception',result)
      exit(0)
    else:
      log.info('after_server_start.sub',result)

if __name__ == '__main__':
  app.run(host='0.0.0.0',port=PORT)
