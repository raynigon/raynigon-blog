---
layout: post
title:  "Database management with(out) Terraform"
author: Simon Schneider
date:   2023-06-11 01:00:00 +0100
categories: infrastructure-as-code
tags: terraform iac postgres k8s
header_image: /img/posts/2023-06-11-header.png
# Social Media
image: /img/posts/2023-05-01-card.png
description: How to manage databases with code in small to medium environments
twitter:
  username: raynigon
---
**TLDR:** When using K8s try to move the database management to manifests and apply them with a custom operator e.g. [Postgres Operator](https://github.com/brose-ebike/postgres-operator/).

# Introduction
Managing Databases in small to medium environments is often a manual task.
Creating new users and adapting the role and permission models is rarely needed.
But the DevOps methodology suggests to use Infrastructure as Code (IaC) for all components.
The major cloud providers offer database as a service solutions.
When the infrastructure of a project is already managed in terraform
and one of these service offerings is used, the next step in automating the database management 
could be to include it in the terraform project.
The following sections will explain how a Postgres database can be managed with terraform 
and how the advantages and disadvantages of this approach affect the daily work of an SRE.

# Managing Postgres with Terraform

I am a big fan of Postgres because it just works and its provided everywhere.
AWS, Google Cloud and Azure all have a Database as a Service offer, 
which can be used instead of hosting it by yourself.
Even self hosting a Postgres database is easy enough for small projects,
because its well documented and a variety of tools is available to manage it.


[![](/img/posts/2023-06-11-database-management-terraform/terraform-registry.jpg)](https://registry.terraform.io/providers/cyrilgdn/postgresql/latest)


In terraform the [cyrilgdn/postgresql](https://registry.terraform.io/providers/cyrilgdn/postgresql/latest) provider can be used to manage the users, roles, grants, extensions, replication and more. The provider is community driven, open source and sometimes has its quirks, but works as expected for most of the standard use cases.

## Example

In this example a postgres configuration will be created in terraform,
which allows to created multiple databases which are owned by service accounts
and can be accessed read only with a developer user account.

The [cyrilgdn/postgresql](https://registry.terraform.io/providers/cyrilgdn/postgresql/latest) provider will be used to apply the configuration to postgres.


<!-- How to include code in jekyll https://stackoverflow.com/questions/27351456/jekyll-including-source-code-via-file -->

## Conclusion
### Advantages

### Disadvantages

# Managing Postgres with K8s

## Example
## Conclusion
### Advantages

### Disadvantages

# References

## Images

The header image comes from Foto von [Juli Kosolapova](https://unsplash.com/@yuli_superson) on [Unsplash](https://unsplash.com/de/fotos/s6aa3O-iyYE)
  