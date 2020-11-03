## Introduction

Demonstartion of extracting a specific data source (deaths per state over time) from HealthData.gov API downloading the source files and loading them into postgres database.

- Business case will drive the data sources of interest which will be required to design schema which can be different per state based on its data source.
- For the purpose of challenge I have used a single data source that contains information per state, I leverage simple pandas transformations to insert it into each state's table.
- it can be extended to account for multiple data sources and multiple tasks can be created for extracting and loading in parallel.

## Development

### Build PostGres docker image

```bash
docker build postgres/ -t postgres:local
```

### Bring all the containers up
```
docker-compose up
```

### Run Visualization
Once the dag has run and container is running, issue the following command
```
python dags/visualization/plotter.py
```
## Notes

- Two seperate postgres instances for airflow and data storage needs
- The instance for storing covid data is named postgres-dev
- Can use celery executors to scale out and distribute
  
---

## Scale out and other Optimizations

### Dag and tasks

- Seperate task instances for each state's sources: searck keys for datasources for each state can be iterated and a task instance can be created for downloading sources per state
- Similarly the load task can remain seperate for each state: read datafrom sources combine and load into its respective table
- Can also leverage postgres operator if sql files are created before hand

### Concurrency

Airflow exposes a lot of different configurations for tuning and paralleizing task instances dag instances connection pools etc. based on resource availibility and data volume those can be configured as desired.


### Executors

- For the purpose of demonstration, I have implemented LocalExecutor, but it makes a lot more sense to instead use something like CeleryExecutor for a production environment which basically uses celery (a distributed task queue) to leverage distributed computing and run tasks across several worker nodes etc.
- can also use queues and pools for specific group of tasks
- Can also leverage the new KubernetesPodOperator which basically containerizes the dag and deploys as its own pod

### Deployment

- Containerized airflow can be orchestrated via Kubernetes, If using CeleryExecutor multiple worker pods per queue can be deployed for distributing
- A Caveat of using Celery Executors is to have all dag dependency installed on worker nodes, instead KubernetesPodOperator can help containerize those dependency instead.
  
---

## Monitoring and Logging

- We can include more robust logging with logbook and also remote logging in case we use CeleryExecutor
- In Addition we can use SlackOperator to fire alerts in case of task failures, these alerts will contain detailed info about failed dag exec date log url etc
- Other frameworks can be utilized to have monitoring/dashboarding around airflow components:
  - In case it is deployed in kubernetes we can use kubernetes based monitoring to look out for resource usage by nodes/pods 
  - Prometheus +Grafana or Elastic logstash+Kibana etc can be used to monitor for airflow and possibly other related infrastructure

