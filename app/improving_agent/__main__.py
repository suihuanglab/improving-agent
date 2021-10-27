#!/usr/bin/env python3

from http import HTTPStatus

import connexion
import flask
import neo4j

from flask import g, jsonify, render_template

from improving_agent import encoder
from improving_agent.src.config import app_config
from improving_agent.src.biolink.spoke_biolink_constants import BIOLINK_SPOKE_NODE_MAPPINGS
from improving_agent.util import get_evidara_logger

driver = neo4j.GraphDatabase.driver(
    app_config.NEO4J_URI,
    auth=(app_config.NEO4J_USER, app_config.NEO4J_PASS),
    max_connection_lifetime=200,
)
logger = get_evidara_logger(__name__)
logger.info('Starting app with configs:\n%s', app_config)


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


def full_text_search(tx, _search):
    r = tx.run(
        'CALL db.index.fulltext.queryNodes("namesAndPrefNames", $_search) '
        'YIELD node, score '
        'RETURN DISTINCT labels(node)[0] AS label, node.identifier AS identifier, node.name AS name, node.pref_name AS pref_name, score '
        'ORDER BY score DESC '
        'LIMIT 15',
        _search=_search
    )
    return [extract_text_result(record) for record in r]


def _check_db(tx):
    res = tx.run('MATCH (n) RETURN n LIMIT 1;')
    result = [r for r in res]
    if result:
        return True
    return False


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
    search_fuzz_or_autocomplete = search
    autocomplete = flask.request.args.get('autocomplete')
    fuzz = flask.request.args.get('fuzz')
    if autocomplete and autocomplete == 'true':
        search_fuzz_or_autocomplete = f'{search}*'
    if fuzz and fuzz == 'true':
        if autocomplete and autocomplete == 'true':
            return 'Must specify only one of fuzz or autocomplete', HTTPStatus.BAD_REQUEST
        search_fuzz_or_autocomplete = f'{search}~'

    _search = f'{search} OR {search}?^6 OR {search}??^4 OR {search}???^3 OR {search_fuzz_or_autocomplete}'
    session = get_db()
    results = session.read_transaction(full_text_search, _search)
    return jsonify({'results': results, 'search': search})


@app.route("/api/hello")
def check_api():
    """Checks for a working connection to this service"""
    return 'OK'


@app.route("/api/hellodb")
def check_db():
    """Checks for a working connection to the database"""
    session = get_db()
    try:
        db_okay = session.read_transaction(_check_db)
        if db_okay is True:
            return 'OK', 200
        else:
            logger.error('Connected to SPOKE, but no nodes were found')
            return 'Error', 500

    except Exception as e:
        logger.error(f'Failed to connect to SPOKE, error was {e}')
        return 'Error', 500


@app.app.teardown_appcontext
def close_db(error):
    if hasattr(g, "db"):
        g.db.close()


def main():
    logger.info("starting improving agent!")
    app.run(port=8080)


if __name__ == "__main__":
    main()
