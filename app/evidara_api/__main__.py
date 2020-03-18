#!/usr/bin/env python3

import connexion
import neo4j
import os

from flask import g, render_template

from evidara_api import config
from evidara_api import encoder
from evidara_api.spoke_constants import BIOLINK_SPOKE_NODE_MAPPINGS
from evidara_api.util import get_evidara_logger
driver = neo4j.GraphDatabase.driver(
    config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASS)
)
logger = get_evidara_logger(__name__)

def get_db():
    """Returns a neo4j driver.session object connected to the SPOKE
    database
    
    Parameters
    ----------
    None
    
    Returns
    -------
    g.db (driver.session): active neo4j database session
    """
    if not hasattr(g, "db"):
        g.db = driver.session()
    return g.db


from evidara_api import core

app = connexion.App(__name__, specification_dir="./openapi/")
app.app.json_encoder = encoder.JSONEncoder
app.add_api(
    "openapi.yaml",
    arguments={"title": "evidARA - a query (im)proving Autonomous Relay Agent"},
    pythonic_params=True,
)


@app.route("/")
def index():
    """returns welcome home page"""
    node_types = list(BIOLINK_SPOKE_NODE_MAPPINGS.keys())
    node_types.remove("0")
    return render_template("home.html", node_types=node_types)


@app.app.teardown_appcontext
def close_db(error):
    if hasattr(g, "db"):
        g.db.close()


def main():
    logger.info("starting evidara!")
    app.run(port=8080, debug=True)


if __name__ == "__main__":
    main()
