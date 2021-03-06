"""
Tests the tracing forwarder monitor
"""
import json
import random
from functools import partial as p
from textwrap import dedent

import pytest
import requests

from tests.helpers.agent import Agent
from tests.helpers.assertions import has_trace_span, tcp_port_open_locally
from tests.helpers.util import wait_for

pytestmark = [pytest.mark.trace_forwarder, pytest.mark.monitor_without_endpoints]

TEST_TRACE = [
    {
        "traceId": "0123456789abcdef",
        "name": "get",
        "id": "abcdef0123456789",
        "kind": "CLIENT",
        "timestamp": 1_538_406_065_536_000,
        "duration": 10000,
        "localEndpoint": {"serviceName": "myapp", "ipv4": "10.0.0.1"},
        "tags": {"env": "prod"},
    }
]

FORWARDER_PATHS = ["/v1/trace", "/api/v1/spans", "/api/v2/spans"]


def test_trace_forwarder_monitor():
    """
    Test basic functionality
    """
    port = random.randint(5001, 20000)
    with Agent.run(
        dedent(
            f"""
        hostname: "testhost"
        monitors:
          - type: trace-forwarder
            listenAddress: localhost:{port}
    """
        )
    ) as agent:
        assert wait_for(p(tcp_port_open_locally, port)), "trace forwarder port never opened!"
        for i, path in enumerate(FORWARDER_PATHS):
            test_trace = TEST_TRACE.copy()
            test_trace[0]["traceId"] = test_trace[0]["traceId"] + str(i)
            resp = requests.post(
                f"http://localhost:{port}{path}",
                headers={"Content-Type": "application/json"},
                data=json.dumps(test_trace),
            )
            assert resp.status_code == 200

            assert wait_for(
                p(has_trace_span, agent.fake_services, trace_id=test_trace[0]["traceId"], tags={"env": "prod"})
            ), "Didn't get span tag"
