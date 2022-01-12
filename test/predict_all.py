import time
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter

cf = CollaborativeFilter(None)
tModelStart = time.time()
cf.import_from_s3()
cf.delta_update()
tModelEnd = time.time()

weights = cf.model.regressor.steps['FMRegressor'].weights
print('weights')
user_id = '128x9v1'
for(k,v) in weights.items():
  akey = k.split('_')
  wtype = akey[0]
  item = akey[1]
  if wtype == 'item':
    results = cf.predict(user_id,[item])
    predicted_value = results[item]
    print(item,predicted_value)
  