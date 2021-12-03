#!/bin/bash
aws_exec=/usr/local/bin/aws
if [[ "$OSTYPE" == "darwin"* ]]; then
  aws_exec=aws
fi
echo 'aws_exec' $aws_exec

most_recent_eventScores=$(aws s3 ls --recursive s3://prod.welco.me/concierge/event_scores | grep 'eventScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_eventScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_eventScores /tmp/eventScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_eventScores" /tmp/eventScores.csv

