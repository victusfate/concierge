from concierge import constants
from concierge.event_queue import ConciergeQueue

cq = ConciergeQueue(constants.event_queue)
cq.poll()

