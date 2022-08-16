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

most_recent_mediaScores=$(aws s3 ls --recursive s3://prod.welco.me/concierge/media_scores | grep 'mediaScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_mediaScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_mediaScores /tmp/mediaScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_mediaScores" /tmp/mediaScores.csv

most_recent_placeScores=$(aws s3 ls --recursive s3://prod.welco.me/concierge/place_scores | grep 'placeScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_placeScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_placeScores /tmp/placeScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_placeScores" /tmp/placeScores.csv

most_recent_tagScores=$(aws s3 ls --recursive s3://prod.welco.me/concierge/tag_scores | grep 'tagScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_tagScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_tagScores /tmp/tagScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_tagScores" /tmp/tagScores.csv

most_recent_publisherScores=$(aws s3 ls --recursive s3://prod.welco.me/concierge/publisher_scores | grep 'publisherScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_publisherScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_publisherScores /tmp/publisherScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_publisherScores" /tmp/publisherScores.csv
