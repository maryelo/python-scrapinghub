# -*- coding: utf-8 -*-
import base64
import os
import pickle
import pytest
import re
import zlib

from scrapinghub.hubstorage.serialization import MSGPACK_AVAILABLE
from scrapinghub import HubstorageClient
from scrapinghub.legacy import Connection


DEFAULT_PROJECT_ID = "2222222"
DEFAULT_ENDPOINT = 'http://storage.vm.scrapinghub.com'
DEFAULT_DASH_ENDPOINT = 'http://33.33.33.51:8080/api/'


TEST_PROJECT_ID = os.getenv('HS_PROJECT_ID', DEFAULT_PROJECT_ID)
TEST_SPIDER_NAME = 'hs-test-spider'
TEST_FRONTIER_SLOT = 'site.com'
TEST_BOTGROUP = 'python-hubstorage-test'
TEST_COLLECTION_NAME = "test_collection_123"
TEST_AUTH = os.getenv('HS_AUTH', 'f' * 32)
TEST_ENDPOINT = os.getenv('HS_ENDPOINT', DEFAULT_ENDPOINT)
TEST_COLLECTION_NAME = "test_collection_123"
TEST_ADMIN_AUTH = os.getenv('AUTH', 'f' * 32)
TEST_USER_AUTH = os.getenv('USER_AUTH', 'e' * 32)
TEST_DASH_ENDPOINT = os.getenv('DASH_ENDPOINT', DEFAULT_DASH_ENDPOINT)


class VCRGzipSerializer(object):
    """Custom ZIP serializer for VCR.py."""

    def serialize(self, cassette_dict):
        # receives a dict, must return a string
        # there can be binary data inside some of the requests,
        # so it's impossible to use json for serialization to string
        cassette_dict = normalize_cassette(cassette_dict)
        compressed = zlib.compress(pickle.dumps(cassette_dict, protocol=2))
        return base64.b64encode(compressed).decode('utf8')

    def deserialize(self, cassette_string):
        # receives a string, must return a dict
        decoded = base64.b64decode(cassette_string.encode('utf8'))
        return pickle.loads(zlib.decompress(decoded))


def normalize_endpoint(uri, endpoint, default_endpoint):
    old = endpoint
    new = default_endpoint

    if old.endswith('/'):
        old = old[:-1]

    if new.endswith('/'):
        new = new[:-1]

    return uri.replace(old, new)


def normalize_cassette(cassette_dict):
    """
    This function normalizes the cassette dict trying to make sure
    we are always making API requests with the same variables:
    - project id
    - endpoint
    - authentication header
    """
    interactions = []
    for interaction in cassette_dict['interactions']:
        uri = interaction['request']['uri']
        uri = uri.replace(TEST_PROJECT_ID, DEFAULT_PROJECT_ID)

        hs_endpoint = TEST_ENDPOINT or HubstorageClient.DEFAULT_ENDPOINT
        uri = normalize_endpoint(uri, hs_endpoint, DEFAULT_ENDPOINT)

        dash_endpoint = TEST_DASH_ENDPOINT or Connection.DEFAULT_ENDPOINT
        uri = normalize_endpoint(uri, dash_endpoint, DEFAULT_DASH_ENDPOINT)

        interaction['request']['uri'] = uri

        if 'Authorization' in interaction['request']['headers']:
            del interaction['request']['headers']['Authorization']
            interaction['request']['headers']['Authorization'] = (
                'Basic {}'.format(
                    base64.b64encode(
                        '{}:'.format('f' * 32).encode('utf-8')
                    ).decode('utf-8')
                )
            )

        interactions.append(interaction)

    cassette_dict['interactions'] = interactions
    return cassette_dict


def pytest_addoption(parser):
    parser.addoption(
        "--update-cassettes", action="store_true", default=False,
        help="test with real services rewriting existing vcr cassettes")
    parser.addoption(
        "--ignore-cassettes", action="store_true", default=False,
        help="test with real services skipping existing vcr cassettes")
    parser.addoption(
        "--disable-msgpack", action="store_true", default=False,
        help="disable messagepack-serialization based tests")


def request_accept_header_matcher(r1, r2):
    """Custom VCR.py matcher by Accept header."""

    def _get_accept_header(request):
        return request.headers.get('Accept', '').lower()

    return _get_accept_header(r1) == _get_accept_header(r2)


@pytest.fixture
def frontier_name(request):
    """Provide a name for test-unique HS frontier."""
    return re.sub('\W+', '-', request.node.nodeid)
