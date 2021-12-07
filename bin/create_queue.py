import boto3
import sys
from sys import platform
from concierge import constants
from bandolier import message_queue

# this script was erroring 
# botocore.exceptions.ClientError: An error occurred (InvalidParameterValue) when calling the CreateQueue operation: Can only include alphanumeric characters, hyphens, or underscores. 1 to 80 in length
# ended up creating it with the aws cli
# aws sqs create-queue --queue-name local_concierge_training.fifo --attributes "{\"FifoQueue\":\"true\",\"ContentBasedDeduplication\":\"false\"}" --debug
# aws sqs create-queue --queue-name d2_concierge_training.fifo --attributes "{\"FifoQueue\":\"true\",\"ContentBasedDeduplication\":\"false\"}" --debug
# aws sqs create-queue --queue-name beta_concierge_training.fifo --attributes "{\"FifoQueue\":\"true\",\"ContentBasedDeduplication\":\"false\"}" --debug
# aws sqs create-queue --queue-name prod_concierge_training.fifo --attributes "{\"FifoQueue\":\"true\",\"ContentBasedDeduplication\":\"false\"}" --debug

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
print({'queue_name': mq.queue_name})
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
