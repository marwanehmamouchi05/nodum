"""Bound HTTP input before parsing or side effects; preserve signed payload bytes."""
import asyncio

from starlette.responses import JSONResponse


class RequestLimitsMiddleware:
    def __init__(self, app, max_bytes=1024 * 1024, body_timeout=10):
        self.app = app
        self.max_bytes = max_bytes
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status, headers={
                "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                "Connection": "close",
            })(scope, receive, send)

        lengths = [value for name, value in scope.get("headers", []) if name.lower() == b"content-length"]
        transfer = any(name.lower() == b"transfer-encoding" for name, _ in scope.get("headers", []))
        declared = None
        if lengths:
            # Reject ambiguous framing if it reaches ASGI. Proxy/server framing
            # must also be tested on the wire; this is not a request-smuggling fix.
            if (len(lengths) != 1 or transfer or not lengths[0].isdigit() or len(lengths[0]) > 10):
                await reject(400, "Invalid request body framing")
                return
            declared = int(lengths[0])
            if declared > self.max_bytes:
                await reject(413, f"Request body exceeds {self.max_bytes} bytes")
                return

        body = bytearray()

        async def collect():
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return "disconnected"
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > self.max_bytes:
                    return "oversized"
                body.extend(chunk)
                if not message.get("more_body", False):
                    return "complete"
                # Yield even if the transport supplies ready/empty chunks.
                await asyncio.sleep(0)

        try:
            result = await asyncio.wait_for(collect(), self.body_timeout)
        except TimeoutError:
            await reject(408, "Request body timed out")
            return
        if result == "disconnected":
            return
        if result == "oversized":
            await reject(413, f"Request body exceeds {self.max_bytes} bytes")
            return
        if declared is not None and declared != len(body):
            await reject(400, "Invalid request body framing")
            return

        buffered = bytes(body)
        del body
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": buffered, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
