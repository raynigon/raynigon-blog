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

Another approach to manage databases is to use a custom operator to manage the database.
This approach is most effective when kubernetes is already a big part of the tech stack.
The [Postgres Operator](https://github.com/brose-ebike/postgres-operator/) is a good example for such an operator.
With a custom operator the database management can be moved to kubernetes manifests 
and the manifests can be applied with the same workflow as the rest of the infrastructure.
The database configuration can be placed next to the application configuration in the same repository.
The developers can read, write and adapt the database configuration without the need to know terraform.
Also the workload on SREs is reduced, because they do not need to write, maintain or review the terraform code.
The operator approach can also make use of the kubernetes RBAC system to authorize database operations.
Only users which can modify specific resources are able to modify the database configuration.

## Example

This example will show how to create a database for the `discovery-service` microservice with the Postgres Operator.

The first step is to let the operator know which servers exist.
These servers can be provisioned with terraform or manually.
They can be hosted in the cloud or on premise.

### Create the PgInstance resource
The operator needs to know the connection details of the server and the credentials to access the server.
These have to be created first and stored in the kubernetes secret `postgres-credentials`.
For this example the secret needs to have the keys `hostname`, `port`, `user`, `password`, `dbname` and `sslmode`.
Afterwards the PgInstance resource can be created. This resource allows the operator to connect to the database server and create databases, roles and privileges.

```yaml
apiVersion: postgres.brose.bike/v1
kind: PgInstance
metadata:
  name: pg-test-001
spec:
  host:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "hostname"
  port:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "port"
  username:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "user"
  password:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "password"
  database:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "dbname"
  sslMode:
    secretKeyRef: 
      name: "postgres-credentials"
      key: "sslmode"
```

### Create the PgDatabase resource

The next step is to create the database. This can be done with the PgDatabase resource.
The PgDatabase resource will create a database in postgres.
To specify on which server the database should be created the `instance` object allows to specify the namespace and name of the PgInstance resource.
  
```yaml
apiVersion: postgres.brose.bike/v1
kind: PgDatabase
metadata:
  name: discovery-service
spec:
  instance:
    namespace: "default"
    name: "pg-test-001"
```

### Create the PgRole resource

The next step is to create the service account user. This can be done with the PgRole resource.
The PgRole resource will create a login role (user) in postgres, generate a random password and store it in a new kubernetes secret.
The secret can be used to access the database from the microservice.
The name of the secret can be specified with the `secret.name` field.
To specify on which server the role should be created the `instance` object allows to specify the namespace and name of the PgInstance resource.
Additionally the `databases` array allows to specify the database privileges for each database.
When the `owner` field is set to `true` the role will be the owner of the specified database.

```yaml
apiVersion: postgres.brose.bike/v1
kind: PgRole
metadata:
  name: discovery-service
spec:
  instance:
    namespace: "default"
    name: "pg-test-001"
  secret:
    name: "service-credentials"
  databases: 
    - name: "discovery-service"
      owner: true
      privileges: ["CONNECT", "CREATE"]
```

### Create the service deployment

After the database and the service account user are created, the service deployment can be created.
In this case a spring boot microservice will be used as example.
The service deployment needs to have the database credentials as environment variables.
The credentials can be read from the secret which was created by the PgRole resource.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discovery-service
spec:
  selector:
    matchLabels:
      app: discovery-service
  replicas: 1
  template:
    metadata:
      labels:
        app: discovery-service
    spec:
      containers:
        - name: discovery-service
          image: "discovery-service:latest"
          env:
            - name: SPRING_DATASOURCE_URL
              valueFrom:
                secretKeyRef:
                  name: "service-credentials"
                  key: "database.discovery-service.jdbc_connection_string"
            - name: SPRING_DATASOURCE_USERNAME
              valueFrom:
                secretKeyRef:
                  name: "service-credentials"
                  key: "user"
            - name: SPRING_DATASOURCE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: "service-credentials"
                  key: "password"
```

The jdbc connection string is stored in the secret by the PgRole resource.
There is one string needed per database and since the operator supports multiple databases per role, the secret can contain multiple jdbc connection strings.
The key of the jdbc connection string is `database.{{name of the database}}.jdbc_connection_string`.

## Conclusion
### Advantages

* The biggest advantage of this approach is that the database management is part of the kubernetes manifests and can be applied with the same workflow as the rest of the application configuration.
* The database management is versioned and can be reviewed in pull requests.
* The database management can be tested and is reproducible on other environments.
* The database management can be applied without the need to have network access to the database server from the developer machine. Since the K8s cluster is usually in the same network as the database server, the operator can access the database server without the need to open the database server to the internet.

### Disadvantages

* The biggest disadvantage of this approach is that the initial setup of the administrator user and the database server is not part of the kubernetes manifests. The database server needs to be created manually or with terraform and the connection details need to be placed in a kubernetes secret.
* The managed of developer users with kubernetes resources can become complicated and sometimes is better placed in the terraform project.
* The operator needs to be installed and maintained.

# Why not both?
At my current job we implemented a hybrid approach to get the best of both worlds.
The database server is created with terraform and the connection details are stored in a kubernetes secret. 
The whole service account and database management is done with the Postgres Operator.
Developer users are created with terraform and the credentials are stored in 1Password.
The terraform project also manages a developer role, which contains all developer users.
When creating a new database, the developer role is granted access to the database and default privileges are applied, so that the developer users can read the content of the database.
This allows to setup database where no developer has access to, but which can still be accessed by the service account.
When a developer leaves the team, the account can easily be removed within terraform.
When new developers join the team, they can be added to the developer role within terraform.
The whole process for developers is transparent, easy to understand and can be reviewed in pull requests.
The whole process for service accounts can be handled without the need of intervention from a SRE.

## Images

The header image comes from Foto von [Juli Kosolapova](https://unsplash.com/@yuli_superson) on [Unsplash](https://unsplash.com/de/fotos/s6aa3O-iyYE)
  