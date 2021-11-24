import pickle
from concierge import data_io
from river import metrics,stats
from river import meta,optim,reco
from river.evaluate import progressive_val_score

metric = metrics.MAE() + metrics.RMSE()

def ratings(df,threshold = 0):
  dataset = []
  for user_item_score in df.itertuples():
    user_id = user_item_score.user_id
    item_id = user_item_score.item_id
    rating  = user_item_score.rating
    dataset.append(({'user': user_id,'item': item_id},rating))
  return dataset

def evaluate(model,metric,dataset):
    _ = progressive_val_score(dataset, model, metric, print_every=25_000, show_time=True, show_memory=True)

def data_stats(metric,dataset):
  mean = stats.Mean()
  for i, x_y in enumerate(dataset, start=1):
      _, y = x_y
      metric.update(y, mean.get())
      mean.update(y)

      if not i % 1_000:
          print(f'[{i:,d}] {metric}')

def learn(model,metric,dataset):
  for x, y in dataset:
    y_pred = model.predict_one(x)      # make a prediction
    metric = metric.update(y, y_pred)  # update the metric
    model = model.learn_one(x, y)      # make the model learn  
  return metric,model

#adding to the global running mean two bias terms characterizing the user and the item discrepancy from the general tendency. The model equation is defined as:
# yhat(x) = ybar + bu_{u} + bi_{i}
def baseline(metric,dataset):
  baseline_params = {
    'optimizer': optim.SGD(0.025),
    'l2': 0.,
    'initializer': optim.initializers.Zeros()
  }
  model = meta.PredClipper(
    regressor=reco.Baseline(**baseline_params),
    y_min=1,
    y_max=5
  )
  # evaluate(model,metric,dataset) # [950,000] MAE: 0.544277, RMSE: 0.98347 – 0:00:41.427565 – 36.36 MB
  return model

# biased matrix factorization, funk svd combination of baseline + funkmf
# yhat(x) = ybar + bu_{u} + bi_{i} + <v_{u},v_{i}>
def bmf(metric,dataset):
  biased_mf_params = {
    'n_factors': 10,
    'bias_optimizer': optim.SGD(0.025),
    'latent_optimizer': optim.SGD(0.05),
    'weight_initializer': optim.initializers.Zeros(),
    'latent_initializer': optim.initializers.Normal(mu=0., sigma=0.1, seed=73),
    'l2_bias': 0.,
    'l2_latent': 0.
  }
  model = meta.PredClipper(
    regressor=reco.BiasedMF(**biased_mf_params),
    y_min=-1,
    y_max=2
  )
  # evaluate(model,metric,dataset) # [950,000] MAE: 0.545842, RMSE: 0.983413 – 0:02:44.577370 – 196.4 MB
  return model

user_item_scores_file = '/tmp/placeScores.csv'
df = data_io.load_dataset(',',user_item_scores_file)
dataset = ratings(df,0)
# data_stats(metric,dataset)
mf = baseline(metric,dataset) 
learn(mf,metric,dataset)
print('metric',metric)
print('model',mf)
model_file = '/tmp/mf.sav'
metric_file = '/tmp/metric.sav'
pickle.dump(mf,    open(model_file, 'wb'))
pickle.dump(metric,open(metric_file,'wb'))

# make sure it works
model  = pickle.load(open(model_file, 'rb'))
metric = pickle.load(open(metric_file, 'rb'))

evaluate(model,metric,dataset)