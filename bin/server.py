from sanic import Sanic
from sanic.response import json

PORT = 5000

app = Sanic("Concierge")

@app.route('/')
async def test(request):
    return json({'hello': 'world'})

if __name__ == '__main__':
    app.run(port=PORT)