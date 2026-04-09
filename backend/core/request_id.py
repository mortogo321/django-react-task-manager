"""
Request-ID middleware. Stamps every request with a unique id and adds
it to the response so logs can be correlated end-to-end.

Honors an upstream `X-Request-ID` header (e.g. from a load balancer)
when present so traces can span multiple services.
"""

import logging
import uuid

log = logging.getLogger("baantask.request")

HEADER = "X-Request-ID"


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.headers.get(HEADER) or uuid.uuid4().hex[:16]
        request.request_id = rid
        try:
            response = self.get_response(request)
        finally:
            log.debug("rid=%s %s %s", rid, request.method, request.get_full_path())
        response[HEADER] = rid
        return response
