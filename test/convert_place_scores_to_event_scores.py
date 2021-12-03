import pandas as pd
import sys

if len(sys.argv) < 3:
  print('usage: python ' + sys.argv[0] + ' <input_csv> <output_csv>')
  exit(1)
headers = ['user_id', 'item_id', 'rating', 'city_id', 'hood_id', 'timestamp', 'hour', 'day']
header_row = None
df = pd.read_csv(sys.argv[1],
                  sep=',',
                  names=headers,
                  header=header_row,
                  dtype={
                      'user_id': str,
                      'place_id': str,
                      'rating': float,
                      'city_id': str,
                      'hood_id': str,
                      'timestamp': int,
                      'hour': str,
                      'day': str
                  },
                  encoding='utf-8')

event_df = df[['user_id', 'item_id', 'rating', 'timestamp']]
event_df.to_csv(sys.argv[2],sep=',',header=False,index=False)