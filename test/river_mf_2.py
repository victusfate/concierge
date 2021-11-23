from concierge import data_io
from river import metrics,stats
from river import meta,optim,reco
from river.evaluate import progressive_val_score

from river import compose
from river import facto
from river import meta
from river import optim
from river import stats

def ratings(df,threshold = 0):
  dataset = []
  for user_item_score in df.itertuples():
    user_id = user_item_score.user_id
    item_id = user_item_score.item_id
    rating  = user_item_score.rating
    dataset.append(({'user': user_id,'item': item_id},rating))
  return dataset

def evaluate(rd,model):
    metric = metrics.MAE() + metrics.RMSE()
    _ = progressive_val_score(rd, model, metric, print_every=25_000, show_time=True, show_memory=True)

def data_stats(dataset):
  mean = stats.Mean()
  metric = metrics.MAE() + metrics.RMSE()

  for i, x_y in enumerate(dataset, start=1):
      _, y = x_y
      metric.update(y, mean.get())
      mean.update(y)

      if not i % 1_000:
          print(f'[{i:,d}] {metric}')

# mimic biased matrix factorization, funk svd combination of baseline + funkmf
# yhat(x) = ybar + bu_{u} + bi_{i} + <v_{u},v_{i}>
def mimic_bmf(dataset):
  fm_params = {
    'n_factors': 10,
    'weight_optimizer': optim.SGD(0.025),
    'latent_optimizer': optim.SGD(0.05),
    'sample_normalization': False,
    'l1_weight': 0.,
    'l2_weight': 0.,
    'l1_latent': 0.,
    'l2_latent': 0.,
    'intercept': 3,
    'intercept_lr': .01,
    'weight_initializer': optim.initializers.Zeros(),
    'latent_initializer': optim.initializers.Normal(mu=0., sigma=0.1, seed=73),
  }

  regressor = compose.Select('user', 'item')
  regressor |= facto.FMRegressor(**fm_params)

  model = meta.PredClipper(
    regressor=regressor,
    y_min=1,
    y_max=5
  )
  evaluate(dataset,model)


user_item_scores_file = '/tmp/placeScores.csv'
df = data_io.load_dataset(',',user_item_scores_file)
dataset = ratings(df,0)
data_stats(dataset)
mimic_bmf(dataset)