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
# for(k,v) in weights.items():
#   akey = k.split('_')
#   wtype = akey[0]
#   item = akey[1]
#   if wtype == 'item':
item_id = '1bb6cc6050fdce88f4e6ff6fc85ae63839528898'
results = cf.predict(user_id,[item_id])
predicted_value = results[item_id]
pval2 = cf.model.predict_one({'user': user_id,'item': item_id})
print(item_id,predicted_value,pval2)
  