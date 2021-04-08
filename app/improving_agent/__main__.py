#!/usr/bin/env python3

from http import HTTPStatus

import connexion
import flask
import neo4j

from flask import g, jsonify, render_template

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


def extract_text_result(result):
    new_result = {}
    new_result['label'] = result.get('label')
    new_result['identifier'] = result.get('identifier')
    new_result['name'] = result.get('name')
    new_result['pref_name'] = result.get('pref_name')
    new_result['score'] = result.get('score')
    return new_result


@app.route("/")
def index():
    """returns welcome home page"""
    node_types = list(BIOLINK_SPOKE_NODE_MAPPINGS.keys())
    return render_template("home.html", node_types=node_types)


@app.route("/node_search")
def search_page():
    """returns node search page"""
    return render_template("node_search.html")


@app.route("/text-search/<search>")
def text_search(search):
    autocomplete = flask.request.args.get('autocomplete')
    fuzz = flask.request.args.get('fuzz')
    if autocomplete and autocomplete == 'true':
        search = f'{search}*'
    if fuzz and fuzz == 'true':
        if autocomplete and autocomplete == 'true':
            return 'Must specify only one of fuzz or autocomplete', HTTPStatus.BAD_REQUEST
        search = f'{search}~'

    session = get_db()
    r = session.run(
        'CALL db.index.fulltext.queryNodes("namesAndPrefNames", $search) '
        'YIELD node, score '
        'RETURN labels(node)[0] as label, node.identifier as identifier, node.name as name, node.pref_name as pref_name, score LIMIT 10',
        search=search
    )

    results = {
        'results': [extract_text_result(record) for record in r.records()],
        'search': search
    }
    return jsonify(results)


@app.app.teardown_appcontext
def close_db(error):
    if hasattr(g, "db"):
        g.db.close()


def main():
    logger.info("starting improving agent!")
    app.run(port=8080)


if __name__ == "__main__":
    main()
