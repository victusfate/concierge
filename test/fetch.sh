#!/bin/bash
aws_exec=/usr/local/bin/aws
if [[ "$OSTYPE" == "darwin"* ]]; then
  aws_exec=aws
fi
echo 'aws_exec' $aws_exec

most_recent_placeScores=$(aws s3 ls --recursive s3://prod.welco.me/recommender/place_scores | grep 'placeScores.csv' | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_placeScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_placeScores /tmp/placeScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_placeScores" /tmp/placeScores.csv

most_recent_tagScores=$(aws s3 ls --recursive s3://prod.welco.me/recommender/tag_scores | sort -r | head -n 1 | awk '{print $4}')
echo $most_recent_tagScores
echo  "aws s3 cp s3://prod.welco.me/$most_recent_tagScores /tmp/tagScores.csv"
$aws_exec s3 cp "s3://prod.welco.me/$most_recent_tagScores" /tmp/tagScores.csv
