from concierge import constants
from concierge.concierge_queue import ConciergeQueue

cq = ConciergeQueue(constants.CF_MEDIA,constants.media_queue,constants.MEDIA_RATINGS_FILE)
cq.poll()

