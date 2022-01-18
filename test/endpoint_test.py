import time
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
import requests


cf = CollaborativeFilter(None)
tModelStart = time.time()
cf.import_from_s3()
cf.delta_update()
tModelEnd = time.time()

item_ids = cf.random_items(30)
user_id = '128x9v1'
rget = requests.get('http://localhost:5000/user/' + user_id + '/items/' + ','.join(item_ids))
print(rget.json())
rpost = requests.post('http://localhost:5000/user/' + user_id + '/items',json={'items': item_ids})
print(rpost.json())