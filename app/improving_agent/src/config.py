import json
import os
from configparser import ConfigParser
from os import path

import boto3
ENV_VAR_APP_ENV_IA = 'APP_ENV_IA'
ENV_VAR_AWS_REGION = 'AWS_REGION'
ENV_VAR_NEO4J_SECRETS_NAME = 'NEO4J_SECRETS_NAME'
ENV_VAR_NEO4J_SPOKE_HOSTNAME = 'NEO4J_SPOKE_HOSTNAME'
ENV_VAR_NEO4J_SPOKE_PASS = 'NEO4J_SPOKE_PASS'
ENV_VAR_NEO4J_SPOKE_USER = 'NEO4J_SPOKE_USER'
ENV_VAR_PSEV_API_KEY = 'PSEV_API_KEY'
ENV_VAR_PSEV_SERVICE_HOSTNAME = 'PSEV_SERVICE_HOSTNAME'
ENV_VAR_PSEV_SECRETS_NAME = 'PSEV_SECRETS_NAME'

APP_ENV_DEV = 'dev'
APP_ENV_ITRB = 'itrb'
APP_ENV_LOCAL = 'local'
VALID_APP_ENVS = [APP_ENV_DEV, APP_ENV_ITRB, APP_ENV_LOCAL]

CONFIG_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'config')


class ApplicationConfig:
    sensitive_data = [
        # ENV_VAR_NEO4J_SPOKE_PASS,
        # ENV_VAR_PSEV_API_KEY,
    ]

    def __init__(
        self,
        app_env,
        configs,
        neo4j_spoke_pass,
        neo4j_spoke_uri,
        neo4j_spoke_user,
        psev_api_key,
        psev_service_hostname,
    ):
        self.APP_ENV = app_env
        self.NEO4J_SPOKE_PASS = neo4j_spoke_pass
        self.NEO4J_SPOKE_USER = neo4j_spoke_user
        self.NEO4J_SPOKE_URI = neo4j_spoke_uri
        self.PSEV_API_KEY = psev_api_key
        if app_env in (APP_ENV_DEV, APP_ENV_LOCAL):
            psev_port = '80'
        else:
            psev_port = '3080'
        self.PSEV_SERVICE_URL = f'http://{psev_service_hostname}:{psev_port}'

        for config, value in configs['DEFAULT'].items():
            setattr(self, config.upper(), value)

        for config, value in configs[app_env].items():
            setattr(self, config.upper(), value)

    def __repr__(self):
        repr_str = ''
        for k, v in self.__dict__.items():
            if k in self.sensitive_data:
                repr_str = f'{repr_str}{k} = ***\n'
            else:
                repr_str = f'{repr_str}{k} = {v}\n'

        return repr_str


def _get_aws_secret(secrets_name):
    # TODO: enable a local-prod-debug profile that passes `profile_name` as kwargs
    region = os.getenv(ENV_VAR_AWS_REGION)
    if not region:
        raise ValueError(f'{ENV_VAR_AWS_REGION} must be set to retrieve secrets')
    session = boto3.Session(region_name=region)
    sm = session.client('secretsmanager')
    secret = json.loads(sm.get_secret_value(SecretId=secrets_name)['SecretString'])
    return secret


def _get_neo4j_creds(app_env, config):
    if app_env == APP_ENV_ITRB:
        neo4j_secrets_name = os.getenv(ENV_VAR_NEO4J_SECRETS_NAME)
        if not neo4j_secrets_name:
            raise ValueError(
                f'{ENV_VAR_NEO4J_SECRETS_NAME} must be set for APP_ENV_IA={APP_ENV_ITRB}'
            )
        secret = _get_aws_secret(neo4j_secrets_name)
        user, pass_ = secret['data'].split('/')
    elif app_env in (APP_ENV_DEV, APP_ENV_LOCAL):
        user = os.getenv(ENV_VAR_NEO4J_SPOKE_USER)
        pass_ = os.getenv(ENV_VAR_NEO4J_SPOKE_PASS)
    else:
        raise ValueError(f'{ENV_VAR_APP_ENV_IA} must be one of {", ".join(VALID_APP_ENVS)}') 

    return user, pass_


def _get_psev_api_key(app_env, config):
    if app_env == APP_ENV_ITRB:
        psev_secrets_name = os.getenv(ENV_VAR_PSEV_SECRETS_NAME)
        if not psev_secrets_name:
            raise ValueError(f'{ENV_VAR_PSEV_SECRETS_NAME} must be set for APP_ENV_IA={app_env}')
        secret = _get_aws_secret(psev_secrets_name)
        api_key = secret['data']
    else:
        api_key = os.getenv(ENV_VAR_PSEV_API_KEY)

    return api_key


app_env = os.getenv(ENV_VAR_APP_ENV_IA, APP_ENV_LOCAL)
if app_env not in VALID_APP_ENVS:
    raise ValueError(f'{ENV_VAR_APP_ENV_IA} must be one of {", ".join(VALID_APP_ENVS)}')

config = ConfigParser()
config.read(path.join(CONFIG_DIR, 'default.cfg'))
config.read(path.join(CONFIG_DIR, f'{app_env}.cfg'))

# neo4j configuration
neo4j_spoke_user, neo4j_spoke_pass = _get_neo4j_creds(app_env, config)
neo4j_hostname = os.getenv(ENV_VAR_NEO4J_SPOKE_HOSTNAME)
if not neo4j_hostname:
    raise ValueError(f'No {ENV_VAR_NEO4J_SPOKE_HOSTNAME} configured in the environment')

neo4j_spoke_uri = f'bolt://{neo4j_hostname}:7687'

# psev configuration
psev_api_key = _get_psev_api_key(app_env, config)
psev_service_hostname = os.getenv(ENV_VAR_PSEV_SERVICE_HOSTNAME)
if not psev_service_hostname:
    raise ValueError(f'{ENV_VAR_PSEV_SERVICE_HOSTNAME} must be set')

app_config = ApplicationConfig(
    app_env,
    config,
    neo4j_spoke_pass,
    neo4j_spoke_uri,
    neo4j_spoke_user,
    psev_api_key,
    psev_service_hostname,
)
