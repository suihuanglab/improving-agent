import os

# neo4j configuration
NEO4J_URI = "bolt://0.0.0.0:7687"
NEO4J_USER = os.getenv("NEO4J_SPOKE_USER")
NEO4J_PASS = os.getenv("NEO4J_SPOKE_PASSWORD")

# psev data locations
PSEV_MATRIX = "./data/psev"
PSEV_MAP = "./data/psev_map"
