from concierge import constants
from concierge.concierge_queue import ConciergeQueue

cq = ConciergeQueue(constants.CF_EVENT,constants.event_queue,constants.EVENT_RATINGS_FILE)
cq.poll()

