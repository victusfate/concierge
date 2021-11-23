from concierge import data_io
from river import metrics,stats
from river import meta,optim,reco
from river.evaluate import progressive_val_score

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

#adding to the global running mean two bias terms characterizing the user and the item discrepancy from the general tendency. The model equation is defined as:
# yhat(x) = ybar + bu_{u} + bi_{i}
def baseline(dataset):
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
  evaluate(dataset,model)

# biased matrix factorization, funk svd combination of baseline + funkmf
# yhat(x) = ybar + bu_{u} + bi_{i} + <v_{u},v_{i}>
def bmf(dataset):
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
    y_min=1,
    y_max=5
  )
  evaluate(dataset,model)  

user_item_scores_file = '/tmp/placeScores.csv'
df = data_io.load_dataset(',',user_item_scores_file)
dataset = ratings(df,0)
data_stats(dataset)
baseline(dataset)
bmf(dataset)