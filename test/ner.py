import requests


text = "Millie's In The Pan\nThe Hideout\nMap Room\nMonteverde"
rget = requests.get('http://localhost:5000/ner/' + text)
print('get',rget.json())
rpost = requests.post('http://localhost:5000/ner',json={'text': text})
print('post',rpost.json())