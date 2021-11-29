# concierge

A continuous learning collaborative filter<sup>1</sup> deployed with a light web server<sup>2</sup>. Distributed updates are a work in progress. 

In progress:  
- exploring redis pubsub updates, and model persistence
- researching real time event bus (kafka?) with playback support to take incremental trained models and augment them to the latest events

1. using [river-ml](https://riverml.xyz/)
2. using [sanic](https://sanic.readthedocs.io/)
