""" THIS IS AN AUTOMATICALLY GENERATED FILE!"""
from __future__ import print_function
import json
from engine import primitives
from engine.core import requests
from engine.errors import ResponseParsingException
from engine import dependencies
req_collection = requests.RequestCollection([])
# Endpoint: /v1/health, method: Get
request = requests.Request([
    primitives.restler_static_string("GET "),
    primitives.restler_basepath(""),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("v1"),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("health"),
    primitives.restler_static_string(" HTTP/1.1\r\n"),
    primitives.restler_static_string("Accept: application/json\r\n"),
    primitives.restler_static_string("Host: {service-ip}:8192\r\n"),
    primitives.restler_refreshable_authentication_token("authentication_token_tag"),
    primitives.restler_static_string("\r\n"),

],
requestId="/v1/health"
)
req_collection.add_request(request)

# Endpoint: /v1/models, method: Get
request = requests.Request([
    primitives.restler_static_string("GET "),
    primitives.restler_basepath(""),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("v1"),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("models"),
    primitives.restler_static_string(" HTTP/1.1\r\n"),
    primitives.restler_static_string("Accept: application/json\r\n"),
    primitives.restler_static_string("Host: {service-ip}:8192\r\n"),
    primitives.restler_refreshable_authentication_token("authentication_token_tag"),
    primitives.restler_static_string("\r\n"),

],
requestId="/v1/models"
)
req_collection.add_request(request)

# Endpoint: /v1/summary, method: Post
request = requests.Request([
    primitives.restler_static_string("POST "),
    primitives.restler_basepath(""),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("v1"),
    primitives.restler_static_string("/"),
    primitives.restler_static_string("summary"),
    primitives.restler_static_string(" HTTP/1.1\r\n"),
    primitives.restler_static_string("Accept: application/json\r\n"),
    primitives.restler_static_string("Host: {service-ip}:8192\r\n"),
    primitives.restler_static_string("Content-Type: "),
    primitives.restler_static_string("application/json"),
    primitives.restler_static_string("\r\n"),
    primitives.restler_refreshable_authentication_token("authentication_token_tag"),
    primitives.restler_static_string("\r\n"),
    primitives.restler_static_string("{"),
    primitives.restler_static_string("""
    "video":"""),
    primitives.restler_custom_payload("video", quoted=True),
    primitives.restler_static_string(""",
    "prompt":"""),
    primitives.restler_custom_payload("prompt", quoted=True),
    primitives.restler_static_string(""",
    "method":"""),
    primitives.restler_fuzzable_group("method", ['SIMPLE','USE_VLM_T-1','USE_LLM_T-1','USE_ALL_T-1','fuzzstring'] , default_enum="USE_ALL_T-1" ,quoted=True),
    primitives.restler_static_string(""",
    "processor_kwargs":
        {
            "process_fps":"""),
    primitives.restler_custom_payload("process_fps"),
    primitives.restler_static_string(""",
            "levels":"""),
    primitives.restler_custom_payload("levels"),
    primitives.restler_static_string(""",
            "level_sizes":"""),
    primitives.restler_custom_payload("level_sizes"),
    primitives.restler_static_string(""",
            "chunking_method":"""),
    primitives.restler_fuzzable_group("chunking_method", ['pelt','uniform','fuzzstring'] , default_enum="pelt", quoted=True),
    primitives.restler_static_string("""
        }
    }"""),
    primitives.restler_static_string("\r\n"),

],
requestId="/v1/summary"
)
req_collection.add_request(request)
