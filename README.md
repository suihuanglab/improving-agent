# imProving Agent

imProving Agent is Autonomous Reasoning Agent built on top of [Scalable Precision Medicine Oriented Knowledge Engine](https://spoke.ucsf.edu/) (SPOKE) and is part of the [NCATS Biomedical Data Translator](https://ncats.nih.gov/translator) Network. It aims to improve user queries by utilizing EHR and multi-omic cohorts to extract the best knowledge for a given concept. Use these links to find out more about [imProving Agents's Data](https://spoke.rbvi.ucsf.edu/docs/index.html), its [algorithms](https://www.nature.com/articles/s41467-019-11069-0), or some of its [multi-omic cohort data](https://www.nature.com/articles/nbt.3870).


### Using imProving Agent
Visit a GUI for the service [here](https://ia.healthdatascience.cloud/) and find the current live definition of the Open API specification [here](https://ia.healthdatascience.cloud/api/v1.2/ui). Find a Jupyter notebook with some basic examples of appropriate Translator API queries [here](examples/improving_agent_examples.ipynb).

### Running and Deploying imProving Agent
The imProving Agent has two major requirements:  
1. A connection to a Neo4j database hosting SPOKE
2. A connection to the PSEV service that contains data used for ranking

These requirements are separately managed, but their connections are
configured via environment variables when starting this service.

First, he Docker image can be built with `docker-compose build web`

All environments must define the following variables:  
- `APP_ENV`: one of `local`, `prod`, or `test`
- `NEO4J_SPOKE_URI`: the bolt URI of the Neo4j database
- `PSEV_SERVICE_URL`: the URL of the PSEV service

If running in the `local` environment, the following variables should be
defined
- NEO4J_SPOKE_USER: the user name for the Neo4j database hosting SPOKE
- NEO4J_SPOKE_PASSWORD: the password for the Neo4j database hosting SPOKE
- PSEV_API_KEY: the API token required to access the PSEV service

If running in `prod` or `test`, these three parameters should be
retrieved automatically from AWS secretsmanager.

Once the environment is properly configured, the user can run `up.sh` to
start the service.
