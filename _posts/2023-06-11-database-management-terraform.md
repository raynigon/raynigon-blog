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

In this example a postgres configuration will be created in terraform, which allows to created multiple databases which are owned by service accounts and can be accessed read only with a developer user account.

![Four microservices each with its own database](/img/posts/2023-06-11-database-management-terraform/microservices-1.svg)

### Create the Database server in Azure
To manage a database we first need to create a PostgreSQL server. The server will be created in azure with minimal configuration applied.

```hcl
locals {
  admin_login     = "admin"
  admin_password  = "super-secret-password-do-not-share"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "br-a-psql-${var.name}"
  resource_group_name    = "test"
  location               = "westeurope"
  version                = 14
  sku_name               = "GP_Standard_D2ds_v4"
  storage_mb             = 32768
  zone                   = "1"
  administrator_login    = local.admin_login
  administrator_password = local.admin_password
}
```
After apply was executed a new server should exists which can now be configured.

### Create the database and service account users

The [cyrilgdn/postgresql](https://registry.terraform.io/providers/cyrilgdn/postgresql/latest) provider will be used to apply the configuration to postgres.

We need to create one database per microservice with one service account user, which owns the database.
Since there could be differences between the microservices, each service name is used as key and the special configuration can be used as value in the map definition.

```hcl
locals {
  microservices = {
    "lading-page-service": {},
    "discovery-service": {},
    "order-service": {},
    "fullfillment-service": {}
  }
}
```

In the next step the service accounts need to be created. The service accounts will be used to access the database from the microservices. The service accounts will be created with a random password and the password can be used later from other resources such as kubernetes secrets.

```hcl
resource "random_password" "service_account_password" {
  for_each = local.microservices

  length           = 32
  special          = false
  override_special = "_%@"
}

resource "postgresql_role" "service_account" {
  for_each = local.microservices

  name     = each.key
  login    = true
  password = random_password.service_account_password.result
}
```

The next step is to create the databases. The databases will be owned by the service accounts and the service accounts will be granted all privileges on the database.

```hcl
resource "postgresql_database" "database" {
  for_each = local.microservices

  name  = each.key
  owner = postgresql_role.service_account[each.key].name
}
```

After apply was executed all service account users and databases should be created. Each microservice can now access its own database with its own service account. But the service accounts are the only users which can access their database. To allow developers to access the database a new user needs to be created and the user needs to be granted access to all databases.


### Create the developer users

In this example the name of the developer users will be stored in the `developers.txt` file, where each row contains exactly one username.
Now the developer users can be created, random passwords should be generated and the passwords should be stored in a yaml file called `developer-credentials.yaml`.

```hcl
data "local_file" "developers" {
  filename = "developers.txt"
}

locals {
  developers = toset(data.local_file.developers.content.split("\n"))
}

resource "random_password" "developer_password" {
  for_each = local.developers

  length           = 32
  special          = false
  override_special = "_%@"
}

resource "postgresql_role" "developer" {
  for_each = local.developers

  name     = each.key
  login    = true
  password = random_password.developer_password[each.key].result
}

resource "local_file" "developer_credentials" {
  filename = "developer-credentials.yaml"
  content  = yamlencode({
    for developer in local.developers :
    developer => {
      username = developer
      password = random_password.developer_password[developer].result
    }
  })
}
```

The next step is to grant the developer users access to all databases. This can be done with the `postgresql_grant` resource. Usually the developer users only have read access to the database, but in this example the developer users will have full access to the database.

```hcl
resource "postgresql_grant" "developer" {
  for_each = local.developers

  database = "*"
  role     = postgresql_role.developer[each.key].name
  privileges = [
    "ALL"
  ]
}
```

After apply was executed all developer users should be created and the credentials should be stored in the `developer-credentials.yaml` file. The developer users can now access all databases with their credentials.
The `developer-credentials.yaml` file is a bad way to manage developer credentials, but it is good enough for this example.
In a real world scenario the developer credentials should be stored in a 1Password vault or a similar solution, which can be accessed by the developers.
For 1Password a [terraform provider](https://registry.terraform.io/providers/1Password/onepassword/latest) exists, which can be used to create and manage secrets in 1Password.

<!-- How to include code in jekyll https://stackoverflow.com/questions/27351456/jekyll-including-source-code-via-file -->

## Conclusion
### Advantages

* The biggest advantage of this approach is that the database management is part of the terraform project and can be applied with the same workflow as the rest of the infrastructure.
* The database management is versioned and can be reviewed in pull requests.
* The database management can be tested and is reproducible on other environments.

### Disadvantages

* The biggest disadvantage of this approach is that queries against the database server need to be performed on every terraform plan or apply execution.
* Therefore the machine on which terraform gets executed need network access to the database server. This also be problem in some environments, where the database server should not accessible from the machine which executed terraform (e.g. developer client).
* When the database managed gets more complex, the terraform plan and apply execution will take longer and longer.


# Managing Postgres with K8s

## Example
## Conclusion
### Advantages

### Disadvantages

# References

## Images

The header image comes from Foto von [Juli Kosolapova](https://unsplash.com/@yuli_superson) on [Unsplash](https://unsplash.com/de/fotos/s6aa3O-iyYE)
  