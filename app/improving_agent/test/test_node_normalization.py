"""This module provides tests for the NodeNormalization client"""
import logging
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import HTTPError

from improving_agent.node_normalization import NodeNormalization
from improving_agent.test.test_config import RUN_REAL_API
from improving_agent.test.client_test_data.node_normalization_data import (
    CHEMICAL_SUBSTANCE_CURIE_PREFIXES,
    GENE_CURIE_PREFIXES,
    NORMALIZED_WATER_NODE,
    SEMANTIC_TYPES
)


class TestNodeNormalization():
    @classmethod
    def setup_class(cls):
        cls.mock_requests_get_patch = patch('improving_agent.node_normalization.requests.get')
        cls.mock_get = cls.mock_requests_get_patch.start()

    @classmethod
    def teardown_class(cls):
        cls.mock_requests_get_patch.stop()

    # get_normalized_nodes()
    def _setup_mock_response(self, status_code=200, json_data=None, text=None, raise_for_status=None):
        # set up errors
        mock_response = Mock()
        if raise_for_status:
            mock_response.raise_for_status.side_effect = raise_for_status

        # set up response
        mock_response.status_code = status_code
        mock_response.text = text
        mock_response.json.return_value = json_data

        self.mock_get.return_value = mock_response

    def test_get_normalized_nodes_good(self):
        self._setup_mock_response(json_data=NORMALIZED_WATER_NODE)

        # instantiate class and query
        nn = NodeNormalization()
        water_curie = "MESH:D014867"
        response = nn.get_normalized_nodes([water_curie])

        assert water_curie == list(response.keys())[0]

    def test_get_normalized_nodes_404(self, caplog):
        caplog.set_level(logging.INFO)

        self._setup_mock_response(
            status_code=404, text="Bad request, good test", raise_for_status=HTTPError("Curie not found")
        )

        nn = NodeNormalization()
        bad_curie = "MESH:D00000"
        with pytest.raises(HTTPError):
            nn.get_normalized_nodes([bad_curie])

        assert "Bad request, good test" in caplog.text

    def test_get_normalized_nodes_only_some(self, caplog):
        caplog.set_level(logging.INFO)

        mock_json_data = {"NCIT:C00000": None, **NORMALIZED_WATER_NODE}
        self._setup_mock_response(json_data=mock_json_data)

        two_curies = set(["MESH:D014867", "NCIT:C00000"])
        nn = NodeNormalization()
        response = nn.get_normalized_nodes(two_curies)

        assert two_curies == set(response.keys())
        assert response["NCIT:C00000"] is None
        assert "Failed to retrieve normalized nodes for ['NCIT:C00000']" in caplog.text

    # get_curie_prefixes()
    def test_get_curie_prefixes(self):
        self._setup_mock_response(json_data=CHEMICAL_SUBSTANCE_CURIE_PREFIXES)

        nn = NodeNormalization()
        response = nn.get_curie_prefixes(["chemical_substance"])

        assert list(response.keys())[0] == "chemical_substance"
        assert list(response["chemical_substance"].keys())[0] == "curie_prefix"

    def test_get_curie_prefixes_multiple(self):
        mock_json_data = {**CHEMICAL_SUBSTANCE_CURIE_PREFIXES, **GENE_CURIE_PREFIXES}
        self._setup_mock_response(json_data=mock_json_data)

        nn = NodeNormalization()
        response = nn.get_curie_prefixes(["chemical_substance", "gene"])
        assert set(response.keys()) == set(["chemical_substance", "gene"])

    def test_get_curie_prefixes_bad(self, caplog):
        bad_semantic_type = "chemicl_substance"
        self._setup_mock_response(
            status_code=404, text=f"No curies discovered for {bad_semantic_type}", raise_for_status=HTTPError()
        )
        with pytest.raises(HTTPError):
            nn = NodeNormalization()
            nn.get_curie_prefixes([bad_semantic_type])

        assert "Failed to get curie prefixes with 404" in caplog.text

    def test_get_curie_prefixes_one_good_one_bad(self, caplog):
        good_semantic_type = "gene"
        bad_semantic_type = "chemicl_substance"
        semantic_types = set([good_semantic_type, bad_semantic_type])
        self._setup_mock_response(
            status_code=404, text=f"No curies discovered for {bad_semantic_type}", raise_for_status=HTTPError()
        )

        with pytest.raises(HTTPError):
            nn = NodeNormalization()
            nn.get_curie_prefixes(semantic_types)

        assert "Failed to get curie prefixes with 404" in caplog.text

    # get_semantic_types()
    def test_get_semantic_types(self):
        self._setup_mock_response(json_data=SEMANTIC_TYPES)

        nn = NodeNormalization()
        response = nn.semantic_types
        # not a great test, just checking that we're still returning a
        # list of str
        assert isinstance(response, list)
        assert all([isinstance(semantic_type, str) for semantic_type in response])

    def test_semantic_types_fails(self, caplog):
        self._setup_mock_response(
            status_code=404, text="Failed to get semantic types", raise_for_status=HTTPError()
        )
        nn = NodeNormalization()
        with pytest.raises(HTTPError):
            response = nn.semantic_types() # NOQA

        assert "Failed to get semantic types with 404 and Failed to get semantic types" in caplog.text


@pytest.mark.skipif(not RUN_REAL_API, reason="Not testing against real API")
class TestNodeNormalizationReal():
    """Tests against the real API - check that the expected structure of
    the real API response has not changed"""

    def test_get_normalized_nodes_real(self):
        nn = NodeNormalization()
        response = nn.get_normalized_nodes(["MESH:D014867"])
        assert set(response["MESH:D014867"].keys()) == set(["id", "equivalent_identifiers", "type"])

    def test_get_curie_prefixes(self):
        nn = NodeNormalization()
        response = nn.get_curie_prefixes(["chemical_substance"])
        assert set(response.keys()) == set(["chemical_substance"])
        assert set(response["chemical_substance"].keys()) == set(["curie_prefix"])

    def test_semantic_types(self):
        nn = NodeNormalization()
        response = nn.semantic_types
        # unpacking happens inside the function, so the call should fail
        # if the structure of the data changes
        assert all([isinstance(semantic_type, str) for semantic_type in response])
