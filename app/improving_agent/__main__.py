#!/usr/bin/env python3

import connexion
import neo4j

from flask import g, render_template

from improving_agent import encoder
from improving_agent.src import config
from improving_agent.src.spoke_biolink_constants import BIOLINK_SPOKE_NODE_MAPPINGS
from improving_agent.util import get_evidara_logger

driver = neo4j.GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USER, config.NEO4J_PASS),
    max_connection_lifetime=200,
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


from improving_agent.src import core # noqa: #E402, E401 

app = connexion.App(__name__, specification_dir="./openapi/")
app.app.json_encoder = encoder.JSONEncoder
app.add_api(
    "openapi.yaml",
    arguments={"title": "imProving Agent - a query (im)proving Autonomous Relay Agent"},
    pythonic_params=True,
)


@app.route("/")
def index():
    """returns welcome home page"""
    node_types = list(BIOLINK_SPOKE_NODE_MAPPINGS.keys())
    return render_template("home.html", node_types=node_types)


@app.app.teardown_appcontext
def close_db(error):
    if hasattr(g, "db"):
        g.db.close()


def main():
    logger.info("starting improving agent!")
    app.run(port=8080)


if __name__ == "__main__":
    main()
