import threading
from concierge import constants
from concierge.concierge_queue import ConciergeQueue

def event_queue_worker():
  cq = ConciergeQueue(constants.CF_EVENT,constants.event_queue,constants.EVENT_RATINGS_FILE)
  cq.poll()
  
def media_queue_worker():
  cq = ConciergeQueue(constants.CF_MEDIA,constants.media_queue,constants.MEDIA_RATINGS_FILE)
  cq.poll()

# separate threads 
event_queue_thread = threading.Thread(target=event_queue_worker,daemon=True)
event_queue_thread.start()

media_queue_thread = threading.Thread(target=media_queue_worker,daemon=True)
media_queue_thread.start()