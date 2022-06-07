import threading
from concierge import constants
from concierge.concierge_queue import ConciergeQueue

def event_queue_worker():
  eq = ConciergeQueue(constants.CF_EVENT,constants.event_queue,constants.EVENT_RATINGS_FILE)
  eq.poll()
  
def media_queue_worker():
  mq = ConciergeQueue(constants.CF_MEDIA,constants.media_queue,constants.MEDIA_RATINGS_FILE)
  mq.poll()

def place_queue_worker():
  pq = ConciergeQueue(constants.CF_PLACE,constants.place_queue,constants.PLACE_RATINGS_FILE)
  pq.poll()

def tag_queue_worker():
  tq = ConciergeQueue(constants.CF_TAG,constants.tag_queue,constants.TAG_RATINGS_FILE)
  tq.poll()

def publisher_queue_worker():
  pq = ConciergeQueue(constants.CF_PUBLISHER,constants.publisher_queue,constants.PUBLISHER_RATINGS_FILE)
  pq.poll()

# separate threads 
event_queue_thread = threading.Thread(target=event_queue_worker)
event_queue_thread.start()

media_queue_thread = threading.Thread(target=media_queue_worker)
media_queue_thread.start()

place_queue_thread = threading.Thread(target=place_queue_worker)
place_queue_thread.start()

tag_queue_thread = threading.Thread(target=tag_queue_worker)
tag_queue_thread.start()

publisher_queue_thread = threading.Thread(target=publisher_queue_worker)
publisher_queue_thread.start()
