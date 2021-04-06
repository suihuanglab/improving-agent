import os

# neo4j configuration
NEO4J_URI = "bolt://host.docker.internal:7687"
NEO4J_USER = os.getenv("NEO4J_SPOKE_USER")
NEO4J_PASS = os.getenv("NEO4J_SPOKE_PASSWORD")

# psev data locations
PSEV_MATRIX = "./data/psev"
PSEV_NODE_MAP = "./data/psev_node_map"
PSEV_DISEASE_MAP = "./data/psev_ncats_disease_map"

# text miner cached node map
TEXT_MINER_NODE_MAP = "./data/text_miner_node_map"

# logging
LOG_LOCATION = "./logs/improving_agent.log"
