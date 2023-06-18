---
layout: post
title:  "Architecture for a Micro Mobility Cloud"
author: Simon Schneider
date:   2023-06-18 01:00:00 +0100
categories: architecture
tags: micro-mobility architecture software-engineering
header_image: /img/posts/2023-06-18-header.png
# Social Media
image: /img/posts/2023-06-18-card.png
description: How to handle data for more than two million bikes.
twitter:
  username: raynigon
---

TLDR: With a modern cloud architecture it is possible to handle the data of more than two million bikes.
The key components are RabbitMQ as MQTT broker, Kafka as event store and message queue and Elasticsearch as time series database.
A microservice architecture allows to scale the cloud horizontally and to provide the services cost efficiently.

# Introduction

Since 2020 I am working for a company which is manufacturing e-bike components and providing an e-bike system.
At the time the systems hardware consists of a motor, a battery and a display.
While working there I had the chance to develop a cloud solution which provides
the interfaces for multiple smartphone apps, IoT devices and other manufacturing related services.
The cloud is currently handling the data of more than two million bikes and is growing rapidly.
In this article I want to share the architecture of the cloud and the lessons learned.

A bike can be connected to the cloud via a smartphone app or via an IoT device.
The smartphone app is used to configure the bike and to provide the user with information about the bike.
The IoT device will give real time updates (e.g. battery level) even when the app is not connected to the bike
and allows the user to control the bike remotely.
The cloud is used to store the data of the bike and to provide the data to the smartphone app.
Additionally data analysis is performed to improve the new and existing products.
The stored data accumulates to multiple billion data points per year.

# Architecture

## Requirements
The cloud architecture has to handle the incoming data from the bikes in real time and store it for later analysis.
The main region in which the e-bikes are used is Europe, therefore then traffic is fluctuating during the day.
Also the traffic varies during the week and the year. Because more people are using the bikes on the weekend and in summer.
The cloud has to be able to handle the traffic peaks and to scale down during the night and winter.
The master data for all bikes need to be stored in the cloud and has to be available for all other services.
The telemetry data has to be stored indefinitely, while still being cost efficient.
All telemetry data has to be available in near realtime (<1s), because can view this data from the smartphone app.
Other departments are never allowed to access data directly, because the users consent is needed for data analysis.
Only the data from users which gave their consent can be used for data analysis.
Due to the amount of data it is not possible to pass a data dump to the data analysis department.

## Overview

<<!-- TODO add overview image here -->>

## Ingestion

### Manufacturing Systems

During the manufacturing process, multiple systems are used to manage the production of the different components
and the bikes itself. Most of the systems are legacy systems and are not able to communicate with the cloud directly.
For the manufacturing of the bikes itself, the systems are used in the plants of the original equipment manufacturers (OEM).
If the OEM is not using the production system correctly, it could happen, that the bike is not registered in the cloud
and can not be used by the customer. This leads to enormous support efforts and costs.
Therefore multiple measures were taken to ensure that the bikes are registered correctly.
But the older data is still not reliable and sometimes has to be checked manually.
Therefore the data from the manufacturing systems has to be cleaned up and checked for consistency,
before it can be stored in the cloud. 
The process of improving the data quality is still ongoing and will be improved in the future.
With the next hardware generation the data quality will be improved, because additional measures were taken,
to ensure a bike is registered correctly and the manufacturing data is consistent.

### Smartphone Apps

The smartphone apps are used to manage the bike and to provide the user with information about the bike.
The user can record rides and navigate with the app. 
The collected data is enriched with the master data from the manufacturing systems
and analyzed to improve the users experience with the bike.
This allows to compensate for missing hardware capabilities, e.g. personalized range estimation.
For the navigation a personalized duration estimation is used, which is based on the users riding behavior.
These features are not possible with the embedded system because it has neither access to the navigation data
nor to all of the users riding data. The cloud on the other hand can process all recorded data to provide these features.

The smartphone apps are recording the riding data and send it to the cloud in batches.
This reduced the battery consumption and allows for more efficient compression to be applied.
The data is sent to the cloud via HTTPs and is published in a Kafka topic.
The ingestion microservice is load balanced and can be scaled horizontally.
This allows to handle traffic spikes while still being cost efficient during low traffic times.

### IoT Devices

The IoT devices are used to provide real time updates to the user and to allow remote control of the bike.
The devices connect to the cloud via MQTT. Each device is authorized by a client side certificate.
The MQTT broker is configured to only allow connections from authorized devices.
For the MQTT broker RabbitMQ is used, because it is easy to scale and provides persistence for AMQP messages.
This is needed in case of a consumer outage. The messages are stored in a queue until the consumer is available again.
Other MQTT brokers like Mosquitto do not provide this feature and would lead to data loss in case of a consumer outage.
The RabbitMQ Broker can be scaled horizontally and is load balanced.
Because the IoT devices are sending data all the time, the traffic is not fluctuating as much as the smartphone app traffic.
The consumer microservice for the IoT devices reads and writes messages to AMQP topics.
The telemetry messages are published to a Kafka topic.
This microservice is can be scaled horizontally as needed, but in this case the bigger bottleneck is the broker itself.
When a spike of messages is received, the broker has to store the messages in the queue.
The consumer can then process the messages as fast as possible, but does not need to process all messages instantly.


## Storage

### Master Data

The master data is stored in a PostgreSQL database.
This allows for fast access to the data and provides a relational data model.
The data gets published to Kafka as a bike entity message.

### Telemetry Data

The telemetry data written to Kafka is stored in Elasticsearch.
This allows to store the data indefinitely and to query the data in near realtime.
The data is stored in a time series data stream, which allows to query the data by time.
The latest versions of Elasticsearch have a different data stream type for time series data[^1].
It allows to to query the data faster and to store the data more efficiently.
This comes with one major drawback: Data points can not be inserted after a specified time period has passed.
This is a problem for the smartphone apps, because they are not always connected to the cloud
and possibly send data with a delay of multiple days to months (e.g. last ride in november is uploaded in march when the app gets opened again).
Since no data can be skipped / deleted, the data has to be stored in the older format,
until a better solution gets developed.

## Analysis


## Images

The header image comes from [Andhika Soreng](https://unsplash.com/@dhika88) on [Unsplash](https://unsplash.com/de/fotos/US06QF_sxu8).
The social card image comes from [Adrien Vajas](https://unsplash.com/@adrien_vj) on [Unsplash](https://unsplash.com/de/fotos/o3_3a_EyNnY).

[^1]: Elasticsearch [Time series data stream](https://www.elastic.co/guide/en/elasticsearch/reference/current/tsds.html)