import threading
from concierge import constants
from concierge.concierge_queue import ConciergeQueue

def event_queue_worker():
  eq = ConciergeQueue(constants.CF_EVENT,constants.event_queue,constants.EVENT_RATINGS_FILE)
  eq.poll()
  
def media_queue_worker():
  mq = ConciergeQueue(constants.CF_MEDIA,constants.media_queue,constants.MEDIA_RATINGS_FILE)
  mq.poll()

# separate threads 
event_queue_thread = threading.Thread(target=event_queue_worker)
event_queue_thread.start()

media_queue_thread = threading.Thread(target=media_queue_worker)
media_queue_thread.start()