from concierge import constants
from concierge.event_queue import ConciergeQueue

cq = ConciergeQueue(constants.event_queue,constants.EVENT_RATINGS_FILE)
cq.poll()

