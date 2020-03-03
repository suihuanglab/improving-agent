#!/usr/bin/env python3

import connexion
import neo4j
import os

from flask import g

from evidara_api import encoder

uri = "bolt://localhost:7687"
neo4j_user = os.environ["NEO4J_SPOKE_USER"]
neo4j_pass = os.environ["NEO4J_SPOKE_PASSWORD"]
driver = neo4j.GraphDatabase.driver(uri, auth=("neo4j", neo4j_pass))

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

app = connexion.App(__name__, specification_dir='./openapi/')
app.app.json_encoder = encoder.JSONEncoder
app.add_api('openapi.yaml',
            arguments={'title': 'evidARA - a query (im)proving Autonomous Relay Agent'},
            pythonic_params=True)

@app.app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

def main():
    app.run(port=8080, debug=True)

if __name__ == '__main__':
    main()
