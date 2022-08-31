# imProving Agent

imProving Agent is Autonomous Reasoning Agent built on top of 
[Scalable Precision Medicine Oriented Knowledge Engine](https://spoke.ucsf.edu/) 
(SPOKE) and is part of the [NCATS Biomedical Data Translator](https://ncats.nih.gov/translator) 
Network. It aims to improve user queries by utilizing EHR and multi-omic
cohorts to extract the best knowledge for a given concept. Use these 
links to find out more about 
[imProving Agents's Data](https://spoke.rbvi.ucsf.edu/docs/index.html), 
its [algorithms](https://www.nature.com/articles/s41467-019-11069-0), 
or some of its [multi-omic cohort data](https://www.nature.com/articles/nbt.3870).


## Using imProving Agent as a client
Find a Jupyter notebook with some basic examples of appropriate
Translator Reasoner API queries [here](examples/improving_agent_examples.ipynb).

## Deploying
### SPOKE database
imProving Agent relies on a bolt connection to a Neo4j instance of SPOKE

### PSEVs
For ranking, imProving Agent relies on PSEVs. PSEVs are accessed
via the psev-service

### Environment variables
Depending on the environment in which imProving Agent is to be run,
a number of environment variables must be set.

#### ITRB deployment
The following variables must be set for deployment in the ITRB test,
staging, and production environments:
- `APP_ENV_IA` should be set to `itrb`
- `AWS_REGION` should be set to the AWS region in which the secrets
noted below are stored.
- `NEO4J_SPOKE_HOSTNAME` should be set to the environment-specific (CI,
Production, Test) hostname of the instance hosting SPOKE
- `NEO4J_SECRETS_NAME` should be set to the environment-specific name
of the secret that contains the authentication credentials for SPOKE
- `PSEV_SECRETS_NAME` should be set to the environment-specific name of
the secrets that will be used to authenticate with the psev-service
- `PSEV_SERVICE_HOSTNAME` the environment-specific hostname of the
instance hosting the psev-service. In most cases, this should be set to
the same value as the NEO4J hostname above

#### Local and dev deployment
- `APP_ENV_IA` should be set to `local` or `dev`
- `NEO4J_SPOKE_HOSTNAME` should be set to the docker network name of
the SPOKE instance to which imProving Agent will connect. In some cases,
e.g. when running against remote databases, this can be set to the
remote hostname
- `NEO4J_SPOKE_PASS` should be set to the password of the local SPOKE
Neo4j instance
- `NEO4J_SPOKE_USER` should be set to the user of the local SPOKE Neo4j
instance
- `PSEV_API_KEY ` should be set to the value of the key that will be
used to connect with the local psev-service instance
- `PSEV_SERVICE_HOSTNAME` should be set to the docker network name of
the psev-service to which imProving Agent will connect
- `AWS_SHARED_CREDENTIALS_FILE` if running locally against remote
resources in AWS, this should be set to the location where `boto3` can
find your AWS credentials

### Networking
The imProving Agent HTTP service will be exposed on port 3031 and uwsgi
stats will be exposed on port 3032. When running locally via
docker-compose, these ports are bound to host ports 3033 and 3034,
respectively.

## Running imProving Agent
Given the depedencies described above, start the service with
`docker-compose up web`
