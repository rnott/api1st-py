import os
import pytest
from wiremock.testing.testcontainer import wiremock_container
from wiremock.client import Mappings, Mapping, MappingRequest, MappingResponse, HttpMethods
from wiremock.constants import Config
import requests

from api1st.resolver import Resolver

@pytest.fixture(scope="session") # (1) # 'module'
def wm_server():
    with wiremock_container(verify_ssl_certs=False, secure=False) as wm:
        Config.base_url = wm.get_url("__admin")
        os.environ["SERVICE_HOST"] = wm.get_base_url()
        Mappings.create_mapping(
            Mapping(
                request = MappingRequest(method=HttpMethods.GET, url="/hello"),
                response = MappingResponse(status=200, body="hello"),
                persistent = False,
            )
        )
        yield wm

def test_get_hello_world(wm_server):
    resp1 = requests.get(wm_server.get_url("/hello"), verify=False)
    assert resp1.status_code == 200
    assert resp1.content == b"hello"