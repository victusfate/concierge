# concierge

A continuous learning collaborative filter<sup>1</sup> deployed with a light web server<sup>2</sup>. Distributed updates are live (real time pubsub + delta training from model snapshots). 

Live:  
- redis pubsub updates, and model persistence
- using redis ordered sets to take incremental trained models and augment them with the latest events

1. using [river-ml](https://riverml.xyz/)
2. using [sanic](https://sanic.readthedocs.io/)

## Architecture

The diagrams follow the [C4 model](https://c4model.com): blue boxes are the running parts of Concierge, grey boxes are systems it depends on. They describe what the code in this repo does. The app backend is not in this repo, so its arrows show what the code here expects of it.

### Containers

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    s_backend["App backend<br/>[Software system]<br/>Not in this repo.<br/>Publishes rating<br/>events, exports<br/>ratings files, queues<br/>training jobs and asks<br/>for scores."]
    s_s3["Amazon S3<br/>[Software system]<br/>Ratings files and<br/>model snapshots, dated<br/>and as latest."]
    s_sqs["Amazon SQS<br/>[Software system]<br/>One FIFO training<br/>queue per model:<br/>event, media, place,<br/>tag, publisher."]
    subgraph sys["Concierge [Software system]"]
        subgraph g_1["This repo"]
            c_server["Concierge server<br/>[Container: Python, Sanic, River]<br/>Holds four live models<br/>(event, media, place,<br/>tag) and learns from<br/>each rating event.<br/>Returns a user's<br/>predicted scores for a<br/>list of items, and<br/>ranks other users by<br/>similarity."]
            c_worker["Training worker<br/>[Container: Python, River]<br/>One thread per queue.<br/>Trains a factorization<br/>machine from a ratings<br/>file and saves it."]
        end
        subgraph g_2["Runs beside it"]
            c_redis[("Redis<br/>[Container: Redis]<br/>Pub/sub channels of<br/>rating events, ordered<br/>sets of recent events<br/>by timestamp, and<br/>cached scores.")]
            c_consul[("Consul<br/>[Container: Consul]<br/>Configuration and AWS<br/>credentials, read at<br/>start.")]
        end
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    style g_1 fill:none,stroke:#b4b9c2,stroke-width:1px
    style g_2 fill:none,stroke:#b4b9c2,stroke-width:1px
    s_backend -->|"Publishes a rating<br/>event<br/>⠀<br/>⠀"| c_redis
    c_redis <-->|"Redis: Delivers the<br/>event on its channel<br/>Concierge server:<br/>Reads events newer<br/>than the model from<br/>the ordered set, then<br/>subscribes<br/>⠀<br/>⠀<br/>⠀<br/>⠀<br/>⠀<br/>⠀<br/>⠀"| c_server
    s_backend -->|"Asks for the user's<br/>scores for a list of<br/>items<br/>⠀<br/>⠀<br/>⠀"| c_server
    c_server -->|"Reads configuration<br/>⠀"| c_consul
    c_server -->|"Loads the latest model<br/>of each type<br/>⠀<br/>⠀"| s_s3
    s_backend -->|"Exports a ratings file<br/>⠀"| s_s3
    s_backend -->|"Queues a training job<br/>⠀"| s_sqs
    c_worker -->|"Polls its queue for a<br/>job<br/>⠀<br/>⠀"| s_sqs
    c_worker -->|"Downloads the ratings<br/>file<br/>⠀<br/>⠀"| s_s3
    c_worker -->|"Caches place scores<br/>for new users and<br/>publisher popularity<br/>⠀<br/>⠀<br/>⠀"| c_redis
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff;
    class s_backend,s_s3,s_sqs external;
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_server,c_worker,c_redis,c_consul container;
```

- **Concierge server** (`bin/server.py`): loads the latest model of each type from S3, replays the events newer than that model from a Redis ordered set, then keeps learning from each event published on Redis. It answers `/user/<id>/events`, `/media`, `/places` and `/tags` with predicted scores, and `/user/<id>/rankings/<users>` with user similarity.
- **Training worker** (`bin/training_queue.py`): one thread per SQS queue. A `train_recommendations` job names a ratings file in S3; the worker trains a factorization machine on it and saves the model and its metric to S3.
- A running server picks up a retrained model the next time it starts.

### Learning from one rating event

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    s_backend["App backend<br/>[Software system]<br/>Not in this repo.<br/>Publishes rating<br/>events, exports<br/>ratings files, queues<br/>training jobs and asks<br/>for scores."]
    subgraph sys["Concierge [Software system]"]
        c_server["Concierge server<br/>[Container: Python, Sanic, River]<br/>Holds four live models<br/>(event, media, place,<br/>tag) and learns from<br/>each rating event.<br/>Returns a user's<br/>predicted scores for a<br/>list of items, and<br/>ranks other users by<br/>similarity."]
        c_redis[("Redis<br/>[Container: Redis]<br/>Pub/sub channels of<br/>rating events, ordered<br/>sets of recent events<br/>by timestamp, and<br/>cached scores.")]
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    s_backend -->|"1. Publishes a rating<br/>event<br/>⠀<br/>⠀"| c_redis
    c_redis -->|"2. Delivers the event<br/>on its channel<br/>⠀<br/>⠀"| c_server
    s_backend -->|"3. Asks for the user's<br/>scores for a list of<br/>items<br/>⠀<br/>⠀<br/>⠀"| c_server
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff;
    class s_backend external;
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_server,c_redis container;
```

### Starting a server

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    s_s3["Amazon S3<br/>[Software system]<br/>Ratings files and<br/>model snapshots, dated<br/>and as latest."]
    subgraph sys["Concierge [Software system]"]
        c_server["Concierge server<br/>[Container: Python, Sanic, River]<br/>Holds four live models<br/>(event, media, place,<br/>tag) and learns from<br/>each rating event.<br/>Returns a user's<br/>predicted scores for a<br/>list of items, and<br/>ranks other users by<br/>similarity."]
        c_redis[("Redis<br/>[Container: Redis]<br/>Pub/sub channels of<br/>rating events, ordered<br/>sets of recent events<br/>by timestamp, and<br/>cached scores.")]
        c_consul[("Consul<br/>[Container: Consul]<br/>Configuration and AWS<br/>credentials, read at<br/>start.")]
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    c_server -->|"1. Reads configuration<br/>⠀"| c_consul
    c_server -->|"2. Loads the latest<br/>model of each type<br/>⠀<br/>⠀"| s_s3
    c_server -->|"3. Reads events newer<br/>than the model from<br/>the ordered set, then<br/>subscribes<br/>⠀<br/>⠀<br/>⠀<br/>⠀"| c_redis
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff;
    class s_s3 external;
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_server,c_redis,c_consul container;
```

### Retraining a model

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    s_backend["App backend<br/>[Software system]<br/>Not in this repo.<br/>Publishes rating<br/>events, exports<br/>ratings files, queues<br/>training jobs and asks<br/>for scores."]
    s_s3["Amazon S3<br/>[Software system]<br/>Ratings files and<br/>model snapshots, dated<br/>and as latest."]
    s_sqs["Amazon SQS<br/>[Software system]<br/>One FIFO training<br/>queue per model:<br/>event, media, place,<br/>tag, publisher."]
    subgraph sys["Concierge [Software system]"]
        c_worker["Training worker<br/>[Container: Python, River]<br/>One thread per queue.<br/>Trains a factorization<br/>machine from a ratings<br/>file and saves it."]
        c_redis[("Redis<br/>[Container: Redis]<br/>Pub/sub channels of<br/>rating events, ordered<br/>sets of recent events<br/>by timestamp, and<br/>cached scores.")]
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    s_backend -->|"1. Exports a ratings<br/>file<br/>⠀<br/>⠀"| s_s3
    s_backend -->|"2. Queues a training<br/>job<br/>⠀<br/>⠀"| s_sqs
    c_worker -->|"3. Polls its queue for<br/>a job<br/>⠀<br/>⠀"| s_sqs
    c_worker -->|"4. Downloads the<br/>ratings file<br/>⠀<br/>⠀"| s_s3
    c_worker -->|"5. Saves the model and<br/>its metric, dated and<br/>as latest<br/>⠀<br/>⠀<br/>⠀"| s_s3
    c_worker -->|"6. Caches place scores<br/>for new users and<br/>publisher popularity<br/>⠀<br/>⠀<br/>⠀"| c_redis
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff;
    class s_backend,s_s3,s_sqs external;
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_worker,c_redis container;
```

<details>
<summary>The same model as a Structurizr workspace</summary>

Paste into [Structurizr](https://structurizr.com) to get context, container and dynamic views.

```
workspace "Concierge" "Real-time recommendation scores from models that keep learning: each rating event updates a live model, and scheduled retraining replaces it." {

    model {
        s_backend = softwareSystem "App backend" "Not in this repo. Publishes rating events, exports ratings files, queues training jobs and asks for scores." "External"
        s_s3 = softwareSystem "Amazon S3" "Ratings files and model snapshots, dated and as latest." "External"
        s_sqs = softwareSystem "Amazon SQS" "One FIFO training queue per model: event, media, place, tag, publisher." "External"
        sys = softwareSystem "Concierge" "Real-time recommendation scores from models that keep learning: each rating event updates a live model, and scheduled retraining replaces it." {
            group "This repo" {
                c_server = container "Concierge server" "Holds four live models (event, media, place, tag) and learns from each rating event. Returns a user's predicted scores for a list of items, and ranks other users by similarity." "Python, Sanic, River"
                c_worker = container "Training worker" "One thread per queue. Trains a factorization machine from a ratings file and saves it." "Python, River"
            }
            group "Runs beside it" {
                c_redis = container "Redis" "Pub/sub channels of rating events, ordered sets of recent events by timestamp, and cached scores." "Redis" "Database"
                c_consul = container "Consul" "Configuration and AWS credentials, read at start." "Consul" "Database"
            }
        }

        s_backend -> c_redis "Publishes a rating event"
        c_redis -> c_server "Delivers the event on its channel"
        s_backend -> c_server "Asks for the user's scores for a list of items"
        c_server -> c_consul "Reads configuration"
        c_server -> s_s3 "Loads the latest model of each type"
        c_server -> c_redis "Reads events newer than the model from the ordered set, then subscribes"
        s_backend -> s_s3 "Exports a ratings file"
        s_backend -> s_sqs "Queues a training job"
        c_worker -> s_sqs "Polls its queue for a job"
        c_worker -> s_s3 "Downloads the ratings file"
        c_worker -> c_redis "Caches place scores for new users and publisher popularity"
    }

    views {
        systemContext sys "context" {
            include *
            autoLayout lr
        }
        container sys "containers" {
            include *
            autoLayout lr
        }
        dynamic sys "v_live" "Learning from one rating event" {
            s_backend -> c_redis "Publishes a rating event"
            c_redis -> c_server "Delivers the event on its channel"
            s_backend -> c_server "Asks for the user's scores for a list of items"
            autoLayout lr
        }
        dynamic sys "v_start" "Starting a server" {
            c_server -> c_consul "Reads configuration"
            c_server -> s_s3 "Loads the latest model of each type"
            c_server -> c_redis "Reads events newer than the model from the ordered set, then subscribes"
            autoLayout lr
        }
        dynamic sys "v_train" "Retraining a model" {
            s_backend -> s_s3 "Exports a ratings file"
            s_backend -> s_sqs "Queues a training job"
            c_worker -> s_sqs "Polls its queue for a job"
            c_worker -> s_s3 "Downloads the ratings file"
            c_worker -> s_s3 "Saves the model and its metric, dated and as latest"
            c_worker -> c_redis "Caches place scores for new users and publisher popularity"
            autoLayout lr
        }
        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "External" {
                background #999999
                color #ffffff
            }
            element "Database" {
                shape Cylinder
            }
            element "Queue" {
                shape Pipe
            }
        }
    }
}
```

</details>

### Before this: the 2020 batch system

Concierge replaced an earlier design that scored in batch beside AWS Personalize. None of it is in this repo; the view below is redrawn from the original design diagram, and the app backend box is added so the user has something to talk to.

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    p_user(["App user<br/>[Person]<br/>Saves, likes, visits<br/>and views places;<br/>uploads media; selects<br/>tags; takes quizzes."])
    s_personalize["AWS Personalize<br/>[Software system]<br/>Managed recommender:<br/>user to places."]
    subgraph sys["Concierge [Software system]"]
        subgraph g_1["Serving"]
            c_app["App backend<br/>[Container]<br/>Records user actions<br/>and returns<br/>recommendations. Not<br/>in the original<br/>drawing."]
            c_db[("Database<br/>[Container]<br/>System of record for<br/>user actions.")]
            c_cache[("Cache<br/>[Container]<br/>Precomputed<br/>neighbourhood scores.")]
        end
        subgraph g_2["Batch scoring"]
            c_export["Cron export<br/>[Container: cron]<br/>Exports user-place<br/>scores on a schedule."]
            c_ncf["NCF recommender<br/>[Container: Python]<br/>Neural collaborative<br/>filtering: user to<br/>places."]
            c_als_places["Implicit ALS: places and users<br/>[Container: Python, implicit]<br/>One model, three<br/>outputs: user to<br/>places, user to users,<br/>place to place."]
            c_als_tags["Implicit ALS: tags<br/>[Container: Python, implicit]<br/>User to tags."]
        end
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    style g_1 fill:none,stroke:#b4b9c2,stroke-width:1px
    style g_2 fill:none,stroke:#b4b9c2,stroke-width:1px
    p_user -->|"Saves, likes, visits,<br/>uploads, selects tags,<br/>quizzes, views<br/>⠀<br/>⠀<br/>⠀"| c_app
    c_app <-->|"App backend: Writes<br/>every action<br/>Database: Recommended<br/>places, read directly<br/>⠀<br/>⠀<br/>⠀<br/>⠀"| c_db
    c_app <-->|"App backend: Sends<br/>saves, likes, visits,<br/>uploads; other actions<br/>optionally<br/>AWS Personalize:<br/>Recommended places<br/>⠀<br/>⠀<br/>⠀<br/>⠀<br/>⠀<br/>⠀"| s_personalize
    c_db -->|"Cron reads user<br/>actions<br/>⠀<br/>⠀"| c_export
    c_export -->|"User-place scores<br/>⠀"| c_ncf
    c_ncf -->|"Recommended places<br/>⠀"| c_app
    c_export -->|"User-place scores<br/>⠀"| c_als_places
    c_als_places -->|"Recommended users and<br/>brands; neighbourhood<br/>scores<br/>⠀<br/>⠀<br/>⠀"| c_app
    c_export -->|"User-tag scores<br/>⠀"| c_als_tags
    c_als_tags -->|"Tag scores<br/>⠀"| c_app
    c_db -->|"Fills the cache<br/>⠀"| c_cache
    c_cache -->|"Neighbourhood scores<br/>⠀"| c_app
    classDef person fill:#08427b,stroke:#052e56,color:#ffffff;
    class p_user person;
    classDef external fill:#999999,stroke:#6b6b6b,color:#ffffff;
    class s_personalize external;
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_app,c_db,c_cache,c_export,c_ncf,c_als_places,c_als_tags container;
```

#### Batch recommendations

```mermaid
%%{init: {"flowchart": {"wrappingWidth": 400, "nodeSpacing": 45, "rankSpacing": 90}, "themeCSS": ".edgeLabel rect, .edgeLabel .labelBkg { fill: none !important; background: none !important; } .edgeLabel p, .edgeLabel span { background: none !important; }"}}%%
flowchart LR
    subgraph sys["Concierge [Software system]"]
        c_app["App backend<br/>[Container]<br/>Records user actions<br/>and returns<br/>recommendations. Not<br/>in the original<br/>drawing."]
        c_db[("Database<br/>[Container]<br/>System of record for<br/>user actions.")]
        c_export["Cron export<br/>[Container: cron]<br/>Exports user-place<br/>scores on a schedule."]
        c_ncf["NCF recommender<br/>[Container: Python]<br/>Neural collaborative<br/>filtering: user to<br/>places."]
        c_als_places["Implicit ALS: places and users<br/>[Container: Python, implicit]<br/>One model, three<br/>outputs: user to<br/>places, user to users,<br/>place to place."]
        c_als_tags["Implicit ALS: tags<br/>[Container: Python, implicit]<br/>User to tags."]
    end
    style sys fill:none,stroke:#8a8f98,stroke-width:1px,stroke-dasharray:6 4
    c_db -->|"1. Cron reads user<br/>actions<br/>⠀<br/>⠀"| c_export
    c_export -->|"2. User-place scores<br/>⠀"| c_ncf
    c_ncf -->|"3. Recommended places<br/>⠀"| c_app
    c_export -->|"4. User-place scores<br/>⠀"| c_als_places
    c_als_places -->|"5. Recommended users<br/>and brands;<br/>neighbourhood scores<br/>⠀<br/>⠀<br/>⠀"| c_app
    c_export -->|"6. User-tag scores<br/>⠀"| c_als_tags
    c_als_tags -->|"7. Tag scores<br/>⠀"| c_app
    classDef container fill:#438dd5,stroke:#2e6295,color:#ffffff;
    class c_app,c_db,c_export,c_ncf,c_als_places,c_als_tags container;
```

Released under the MIT License
