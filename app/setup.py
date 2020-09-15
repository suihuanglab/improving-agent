# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "improving_agent"
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
    "numpy>=1.18.1",
    "neo4j>=1.7.0",
    "python_dateutil>=2.6.0",
    "python-Levenshtein>=0.12",
    "requests>=2.23"
]

setup(
    name=NAME,
    version=VERSION,
    description="imProving Agent",
    author_email="brett.smith@isbscience.org",
    url="",
    keywords=["OpenAPI", "imProving Agent"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['improving_agent=improving_agent.__main__:main']},
    long_description="""\
    imProving Agent - a SPOKE-based Autonomous Reasoning Agent in the NCATS Translator Network
    """
)

