import json
import os
from configparser import ConfigParser
from os import path

import boto3

APP_ENV_LOCAL = 'local'
APP_ENV_PROD = 'prod'

CONFIG_SECTION_DEFAULT = 'DEFAULT'

NEO4J_PASS = 'NEO4J_PASS'
NEO4J_URI = 'NEO4J_URI'
NEO4J_USER = 'NEO4J_USER'

PSEV_API_KEY = 'PSEV_API_KEY'


CONFIG_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), 'config')


class ApplicationConfig:
    sensitive_data = [NEO4J_PASS, PSEV_API_KEY]

    def __init__(
        self,
        app_env,
        configs,
        neo4j_user,
        neo4j_pass,
        neo4j_uri,
        psev_api_key,
        psev_url
    ):
        self.APP_ENV = app_env
        self.NEO4J_USER = neo4j_user
        self.NEO4J_PASS = neo4j_pass
        self.NEO4J_URI = neo4j_uri

        self.PSEV_API_KEY = psev_api_key
        self.PSEV_SERVICE_URL = psev_url

        for config, value in configs[CONFIG_SECTION_DEFAULT].items():
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


def _get_aws_secret(secret_name):
    # TODO: enable a local-prod-debug profile that passes `profile_name` as kwargs
    session = boto3.Session(region_name='us-west-2')
    sm = session.client('secretsmanager')
    secret = json.loads(sm.get_secret_value(SecretId=secret_name)['SecretString'])
    return secret


def _get_neo4j_creds(app_env, config):
    if app_env == APP_ENV_PROD:
        secret = _get_aws_secret(config[app_env]['n4j_creds_name'])
        user, pass_ = secret['data'].split('/')
    else:
        user = os.getenv('NEO4J_SPOKE_USER')
        pass_ = os.getenv('NEO4J_SPOKE_PASSWORD')

    return user, pass_


def _get_neo4j_uri():
    return os.environ['NEO4J_SPOKE_URI']


def _get_psev_uri():
    return os.environ['PSEV_SERVICE_URL']


def _get_psev_api_key(app_env, config):
    if app_env == APP_ENV_PROD:
        secret = _get_aws_secret(config[app_env]['psev_api_name'])
        api_key = secret['data']
    else:
        api_key = os.getenv('PSEV_API_KEY')

    return api_key


app_env = os.getenv('APP_ENV', APP_ENV_LOCAL)
config = ConfigParser()
config.read(path.join(CONFIG_DIR, 'default.cfg'))
config.read(path.join(CONFIG_DIR, f'{app_env}.cfg'))

# neo4j configuration
neo4j_user, neo4j_pass = _get_neo4j_creds(app_env, config)
neo4j_uri = _get_neo4j_uri()

# psev configuration
psev_api_key = _get_psev_api_key(app_env, config)
psev_url = _get_psev_uri()

app_config = ApplicationConfig(
    app_env,
    config,
    neo4j_user,
    neo4j_pass,
    neo4j_uri,
    psev_api_key,
    psev_url
)
