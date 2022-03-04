import boto3
import sys
from sys import platform
from concierge import constants
from bandolier import message_queue


def create_queue(name):
  print({
    'event_training queue': name,
    'env': constants.ENVIRONMENT,
    'region_name': constants.AWS_REGION,
    'profile_name': constants.AWS_PROFILE
  })

  # Create a SQS queue
  mq = message_queue.MessageQueue(name=name,
    env=constants.ENVIRONMENT,
    region_name=constants.AWS_REGION,
    profile_name=constants.AWS_PROFILE)
  print({'queue_name': mq.queue_name})
  mq.create_queue()

  mq = message_queue.MessageQueue(name=name,
    env='d2',
    region_name=constants.AWS_REGION,
    profile_name=constants.AWS_PROFILE)
  mq.create_queue()

  mq = message_queue.MessageQueue(name=name,
    env='beta',
    region_name=constants.AWS_REGION,
    profile_name=constants.AWS_PROFILE)
  mq.create_queue()

  mq = message_queue.MessageQueue(name=name,
    env='prod',
    region_name=constants.AWS_REGION,
    profile_name=constants.AWS_PROFILE)
  mq.create_queue()

create_queue(constants.EVENT_QUEUE_ROOT_NAME)
create_queue(constants.MEDIA_QUEUE_ROOT_NAME)
