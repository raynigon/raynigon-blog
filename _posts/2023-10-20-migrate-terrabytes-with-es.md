---
layout: post
title:  "Migrate terabytes of data in Elasticsearch"
author: Simon Schneider
date:   2123-10-20 13:00:00 +0100
categories: development
tags: software-engineering python elasticsearch
header_image: /img/posts/2023-10-20-header.png
# Social Media
image: /img/posts/2023-10-20-card.png
description: How to migrate terabytes of data in elasticsearch
twitter:
  username: raynigon
---

TLDR: When migrating data with elasticsearch there are two options, the first one is to use the reindex functionality and apply a painless script.
This approach has the limitation that one event can only be mapped to one other event. Therefore if a one to one mapping is not possible,
the second approach is needed: Migrating the data with an external application.

# Introduction
Since 2020 I am working on a project for a company which is manufacturing e-bike components 
and providing a e-bike systems. The company manufactured over 2 million bikes which are used all over the world[^1].
At the time the systems hardware consists of a motor, a battery and a display.
With the Brose E-Bike App[^2] the telemetry data of this components is collected and analyzed (if the user agrees).
The data is stored in a elasticsearch cluster and is used for various purposes, such as:
- Generate statistics for the user
- Monitor rollout of new firmware versions
- Detect errors of the system in the field

The data is stored as events in an elasticsearch data stream[^3].
The data stream is partitioned automatically by elasticsearch.
The initial event schema consisted of only two events.
The first event is the `telemetry` event which contains the telemetry data of the system.
The second event is the `snapshot` event which contains the static information of the system.
The `snapshot` event is created when the app connects to the system.
The second iteration of the event schema split the `telemetry` event into multiple events.
One event for the motor, one for the battery and one for the display.
The new schema was only used during ride recording and the old schema was still used in parallel.
This was done to ensure no data is lost, when ride recording was inactive.
The third iteration of the event schema should replace both previous schemas.
Therefore the data of the old schemas had to be migrated to the new schema.

# Migration options in Elasticsearch
Elasticsearch offers two options to migrate data inside the cluster.
The first option is to use the reindex functionality and apply a painless script[^4].
This options is very easy to use and can be done with a single request.
While it is fast and does not require any external application, it has some limitations.
The main limitation is that one event can only be mapped to one other event.
The second option is to use an external application to read the data from the old index and write it to the new index.
This option is more complex and requires an external application, but it is more flexible and can be used for more complex migrations.

# Migration plan
The first option can not be used for the migration, because the new schema has multiple events for one old event.
Therefore we needed to create an external application which fetches the events, converts them and writes them to the new index.





# References

## Images

The header and the the social card image comes from [Taylor Vick](https://unsplash.com/@tvick) on [Unsplash](https://unsplash.com/de/fotos/%EC%BC%80%EC%9D%B4%EB%B8%94-%EB%84%A4%ED%8A%B8%EC%9B%8C%ED%81%AC-M5tzZtFCOfs).

## Citations


[^1]: Press release [Two million e-bike drives](https://www.brose.com/de-en/press/brose-celebrates-two-million-ebike-drives.html)
[^2]: [Brose E-Bike App](https://www.brose-ebike.com/de-de/app-kompatible-ebikes/)
[^3]: Elasticsearch  Documentation [Data Streams](https://www.elastic.co/guide/en/elasticsearch/reference/current/data-streams.html)
[^4]: Elasticsearch  Documentation [Reindex](https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-reindex.html)