# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "evidara_api"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python_dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="evidARA - a query (im)proving Autonomous Relay Agent",
    author_email="brett.smith@isbscience.org",
    url="",
    keywords=["OpenAPI", "evidARA - a query (im)proving Autonomous Relay Agent"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['evidara_api=evidara_api.__main__:main']},
    long_description="""\
    evidARA - a query (im)proving Autonomous Relay Agent and a subset of a fork of the NCATS ReasonerStandardAPI
    """
)

