import pandas as pd
import time
import os
from concierge import data_io
from concierge import constants
from concierge.collaborative_filter import CollaborativeFilter
from river import metrics
import redis

cache = redis.Redis(host=constants.REDIS_HOST, port=6379, db=0)   

df = data_io.load_dataset(',',constants.RATINGS_FILE)
max_ts,dataset = CollaborativeFilter.df_to_timestamp_and_dataset(df)
cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
cf.timestamp = max_ts

# cf.data_stats(dataset)
tLearnStart = time.time()
cf.learn(dataset,max_ts)
# cf.evaluate(dataset)
tLearnEnd = time.time()
print('tLearn',tLearnEnd-tLearnStart)

# tCacheSetStart = time.time()
# cf.cache_set_metric_and_model()
# tCacheSetEnd = time.time()
# print('tCacheSet',tCacheSetEnd-tCacheSetStart)

# tSaveStart = time.time()
# cf.save_to_file()
# tSaveEnd = time.time()
# print('tSave',tSaveEnd-tSaveStart)

# # make sure it works
# cache_cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
# tCacheGetStart = time.time()
# cache_cf.cache_get_metric_and_model()
# tCacheGetEnd = time.time()
# print('tCacheGet',tCacheGetEnd-tCacheGetStart)

timestamp = int(time.time())
new_model_metric_path = '/tmp/' + str(timestamp)
cf.export_to_s3(new_model_metric_path)
# clear local model files
os.system('rm -rf ' + new_model_metric_path)
os.system('rm /tmp/model.sav')
os.system('rm /tmp/metric.sav')


# make sure it works
# load_cf = CollaborativeFilter(CollaborativeFilter.fm_model(),metrics.MAE() + metrics.RMSE())
load_cf = CollaborativeFilter(None)
tLoadStart = time.time()
load_cf.import_from_s3()
# load_cf.load_from_file()
tLoadEnd = time.time()
print('tImport from s3',tLoadEnd-tLoadStart)


print('metric',cf.metric)
print('model',cf.model)

user_id   = '128x9v1'
place_ids = ['iibwqpe4-1hsmqbr','gcjsio4c-1qqsc7h','gcjskoy4-lp9my1','gcjskvs4-derkhm','gcjsl00k-th59ji','gcjt0nk4-1f3vq6z','gcjscauk-1f3vq6z','gcjsldzg-17t6qla','gcjlze4c-5lpwip','gcjsbtwc-1aep9i6','gcjm2mpo-d9gua8','gcjskuw4-vr4t4i','gcjsl4us-brmv3t','gcjsch7w-pvwwwf','gcjsdkzo-1otm62s','gcjs8ggk-1pnj06a','gcjslcto-1ccf2i6','gcjsn164-1ll9zs0','gcjslcpw-7h5p57','gcjskkjo-jki4o6','gcjs82y4-copotk','gcjsakpg-51ii86','gcjslmak-y3s2xj','gcjs8pv0-xcmahz','gcjskqxw-95si0p','gcjs9yp0-1io2ziw','gcjs9q9o-1xyyntn','gcjskop0-1rjefxj','gcjsjzfw-1v0ta0l','gcjs8ehw-6uxteb','gcjs82y4-em453w','gcjsbuf8-pxaunf','gcjsd018-198owxr','gcjsjg38-m6kqn8','gcjs7zj0-ts27tf','gcjsjecs-1tkgxjz','gcjsk1n0-ut8h69','gcjsb1kc-1izg0d7','gcjscux8-mcgmpo','gcjscvss-1vp0ncl','gcjsfyq4-3aitoq','gcjsjv6c-22dmed','gcjsjcqk-1578cx2','gcjs9tyk-1vg1djn','gcjm0y6k-15v98dr','gcjmc5ck-k192z4','gcjs59no-1hrlmd9','gcjskt4s-1m4wvkg','gcjskzjg-1uzu12x','gcjs894k-v5vcbk','gcjsktqs-dqj0b8','gcjskxw4-tiu4nb','gcjs5b6k-11r9b8t','gcjsf4v0-1gzgecg','gcjs8bks-8anqr6','gcjsl0ms-umevio','gcjltyp0-1uvbz1e','gcjsll8k-1sh0i5u','gcjs8ygs-ncw0qt','gcjs91g4-ftkwej','gcjsl0ik-e4o2ls','gcjsll8k-1gp6ivv','gcjs9rfg-pxaunf','gcjs8ebg-1rm88z6','gcjlrvhw-1cd3eab','gcjlymfg-1m4syma','gcjms03o-27wfm5','gcjs6tn8-qk4n0c','gcjs7864-1v7tlsz','gcjs787g-11r9b8t','gcjs78ec-ybuzuw','gcjs8xr8-1xjdfp2','gcjs90lo-1cc3r89','gcjs91q4-us1y9g','gcjs9wm4-1klghvn','gcjsazok-12xfp74','gcjsb6l8-1rxz45j','gcjsd8ws-7pctg0','gcjsdmfo-14jrn0j','gcjsdn3o-12f6mr2','gcjsf4u4-c3cr71','gcjsfwgc-149cau8','gcjsj6h0-1iva2u3','gcjsjz10-1s5e0go','gcjsjz7o-1iqyg8f','gcjsk1qk-za2fsq','gcjskbtg-196a4vp','gcjskgb8-gfcozh','gcjskiv0-1iyafka','gcjskmac-1lfguzc','gcjskook-19mwyzz','gcjsks6s-f0vyy9','gcjsks78-r5jn7u','gcjsl0qs-nz89v1','gcjsl5do-mcgmpo','gcjsljjg-4lh643','gcjslsy4-1dgxko3','gcjslvw4-12yf3p8','gcjsn3pw-1d6ctai','gcjsovhw-warn63','gck8wz5w-nyun28','gck90cuc-1brx3u1','gcjs8ad8-ms07d3','gcjs8c70-1eyic8q','gcjs9q9o-15a27hu','gcjsaqv8-u0tlz8','gcjsb6ik-1eusyrx','gcjsjgb8-55h91h','gcjsjo10-19qttvq','gcjsjrdw-bg0cw0','gcjsjtf0-a1i3sg','gcjsjtik-1lii6hq','gcjsksss-1mv7ga1','gcjskt04-hfmkr0','gcjskws4-9cjmr5','gcjsnogk-sp4qyu','gck8zdfo-gzbzxi','gcjsk53g-dzwvpg','gcjsk9bg-b81r1','gcjskd70-1h46vke','gcjskdxo-dmknq4','gcjskicc-35x8cv','gcjsklr8-159iysk','gcjskn3w-1gugxvy','gcjskp1w-u6rgp8','gcjsks78-e3au68','gcjsks78-fpoulq','gcjlfbrg-je2k9p','gcjm1xec-15qmqxr','gcjs1awk-kmmcub','gcjs4vzg-9ddyki','gcjs4yr8-yl4etp','gcjs52xo-1yw4klo','gcjs7uf8-1oyxn94','gcjs89is-imhpxk','gcjsa5pg-1d3rn59','gcjsblws-1fntjol','gcjscfis-o1g15v','gcjsdgc4-iks7nd','gcjselmc-l8vl9z','gcjsf4v0-1vg3tym','gcjsjojg-15bouta','gcjsjoos-ghujtd','gcjsk0to-14ztndx','gcjsk350-1xk62r1','gcjsk3p0-etup6r','gcjskdmk-11somlv','gcjskgfg-79q9vh','gcjskoy4-74ohcm','gcjskplw-tmw1tc','gcjskxw4-1y8blcr','gcjsl2l0-n225c','gcjsl6uc-1erq1ew','gcjsljbo-14pxd80','gcjs81cs-kc1yvt','gcjskmac-uh7whh','gcjskjk4-1kim31f','gcjsl06k-1jbviwo','gcjsktmk-1fswgk1','gcjscmbg-l96r5h','gcjlyd38-ps95m1','gcjskf1g-4hu0mj','gcjsclak-10z9re0','gcjskzks-o4r6z2','gcjsc50c-1hskcs','gcjs91f0-inikst','gcjsl23w-13w3biv','gcjlrvhw-59il9i','gcjskwx8-abuh07','gcjsldm4-1w375zz','gcjskoa4-sa3ghr','gcjs8b7g-1ek98mb','gcjsk3b0-ljoc0t','gcjskoxg-1vsad96','gcjske7o-kj8xwh','gcjsl6do-bbiy6y','gcjsljjg-1u1dala','gcjslikc-mhkv03','gcjs98ic-1dnuqlb','gcjsjea4-jtmnt4','gcjlrv6s-sicvoy','gcjsas4s-e1wp71','gcjsk7wc-1liwyfg','gcjsksss-gvkae7','gcjs8ebg-3jayet','gcjsb2i4-9ax5cg','gcjsl6p0-tiu4nb','gcjskeas-1pi4iiq','gcjsa6x8-3g8erl','gcjsk24s-15qmwzw','gcjs82is-1budbce','gcjsovj8-1l39fv5','gcjt0nvo-1u5ymvj','gcjls8ec-1r87a61','gcjsjrgs-y556aa','gcjskoa4-eqirvq','gcjslwto-ppets1','gcjmvm8k-pxo1f4','gcjsk7t8-u4v8u','gcjsaj1o-18jv4t6','gcjsabpg-13jf38x','gcjs87qk-144gdsu','gcjskm6c-11dzulf','gcjsjr2s-1ifqz0u','gcjsksss-1puny7','gcjs8b78-f73fsm','gcjs9718-19fjczq','gcjsciqc-yh49w0','gcjs8c84-ksy6qj','gcjsckgk-pxaunf','gcjs83x8-6nsoo6','gcjskrz0-1wr4px4','gcjsk5cs-wu3xwc','gcjsjx1o-1u8gfch','gcjs9vsk-bjlpmu','gcjsl4zw-aehlm9','gcjlw6uc-t5h8b2','gcjsbbkk-1nw06i8','gcjs8144-kk9shd','gcjshk2k-1muub9u','gcjsjv6s-18t5cfo','gcjs8c2k-nz968d','gcjsaagc-12nfdhr','gcjsl0ks-1xxx430','gcjsfrb8-ng9ei3','gcjsliro-bexfrp','gcjsl12k-1j41eet','gcjskox8-1sr60yn','gcjsks8s-1se14iv','gcjsjp44-1eqq5vw','gcjm0uw4-1dh8c8z','gcjm11z8-4f9wl6','gcjsbgz8-btpvzg','gcjs82ro-u5zi27','gcjskrws-llx6ep','gcjslerw-5caknw','gcjsf038-1gzgecg','gcjm32g4-rckfca','gcjs8c10-17wmyll','gcjsr718-kppkbm','gcjsjdqk-172t98k','gcjm33dg-14gd5lx','gcjsf4v0-146nc5r','gcjs8ggk-1lgqc2a','gcjsa5pg-upf3fg','gcjsb00s-hlrj1r','gcjslzl0-ppets1','gcjslkik-23a934','gcjm2i6c-1cmcn7r','gcjs8jrw-1gd1myx','gcjscfvo-149cau8']
# print('cache prediction')
# scores = cache_cf.predict(user_id,place_ids)
# for place_id,score in scores.items():
#   print(place_id,score)

print('load prediction')
scores = load_cf.predict(user_id,place_ids)
for place_id,score in scores.items():
  print(place_id,score)
