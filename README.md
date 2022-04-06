# concierge

A continuous learning collaborative filter<sup>1</sup> deployed with a light web server<sup>2</sup>. Distributed updates are live (real time pubsub + delta training from model snapshots). 

Live:  
- redis pubsub updates, and model persistence
- using redis ordered sets to take incremental trained models and augment them with the latest events

1. using [river-ml](https://riverml.xyz/)
2. using [sanic](https://sanic.readthedocs.io/)

Released under the MIT License
