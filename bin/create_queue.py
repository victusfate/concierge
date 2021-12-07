import boto3
import sys
from sys import platform
from concierge import constants
from bandolier import message_queue

print({
  'training queue': constants.TRAINING_QUEUE_ROOT_NAME,
  'env': constants.ENVIRONMENT,
  'region_name': constants.AWS_REGION,
  'profile_name': constants.AWS_PROFILE
})

# Create a SQS queue
mq = message_queue.MessageQueue(name=constants.TRAINING_QUEUE_ROOT_NAME,
  env=constants.ENVIRONMENT,
  region_name=constants.AWS_REGION,
  profile_name=constants.AWS_PROFILE)
mq.create_queue()

mq = message_queue.MessageQueue(name=constants.TRAINING_QUEUE_ROOT_NAME,
  env='d2',
  region_name=constants.AWS_REGION,
  profile_name=constants.AWS_PROFILE)
mq.create_queue()

mq = message_queue.MessageQueue(name=constants.TRAINING_QUEUE_ROOT_NAME,
  env='beta',
  region_name=constants.AWS_REGION,
  profile_name=constants.AWS_PROFILE)
mq.create_queue()

mq = message_queue.MessageQueue(name=constants.TRAINING_QUEUE_ROOT_NAME,
  env='prod',
  region_name=constants.AWS_REGION,
  profile_name=constants.AWS_PROFILE)
mq.create_queue()
