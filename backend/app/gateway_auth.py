"""
Engine-side check that a request came through the Splunk gateway. Pure ASGI, so it covers HTTP and WebSocket connections.

This is not user authorization: Splunk authenticates the user and the gateway enforces roles. The key only closes the other door,
so reaching the engine's socket or port is not a way around Splunk.

* PULSEFORGE_GATEWAY_KEY set: every connection except GET /api/health must carry the matching X-PulseForge-Gateway-Key.
* PULSEFORGE_REQUIRE_GATEWAY_KEY=1 (set by the Splunk-managed launcher): the same, and with no key configured every connection is
  refused (fail closed). The engine bootstrap also refuses to start in that mode without a key.
* Neither set: unchanged behaviour, for the standalone engine and the demo lab.
"""
import hmac
import json
import os

KEY_HEADER = b"x-pulseforge-gateway-key"
_BODY = json.dumps({"detail": "Engine requests must come through the Splunk gateway"}).encode()


class GatewayKeyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            key = os.environ.get("PULSEFORGE_GATEWAY_KEY", "")
            required = os.environ.get("PULSEFORGE_REQUIRE_GATEWAY_KEY") == "1"
            if (key or required) and not (scope["type"] == "http" and scope["method"] == "GET" and scope["path"] == "/api/health"):
                supplied = next((v for k, v in scope["headers"] if k == KEY_HEADER), b"")
                if not key or not hmac.compare_digest(supplied, key.encode()):
                    if scope["type"] == "http":
                        await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(_BODY)).encode())]})
                        await send({"type": "http.response.body", "body": _BODY})
                    else:
                        await send({"type": "websocket.close", "code": 1008})
                    return
        await self.app(scope, receive, send)
