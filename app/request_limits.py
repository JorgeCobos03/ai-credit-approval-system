from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound uploads even when Content-Length is absent (chunked requests)."""

    def __init__(self, app, max_bytes=9 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] in ('GET', 'HEAD', 'OPTIONS'):
            return await self.app(scope, receive, send)
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            if total > self.max_bytes:
                response = JSONResponse({'detail': 'La solicitud supera el límite de 9 MB.'}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(message.get('body', b''))
            if not message.get('more_body', False):
                break
        body = b''.join(chunks)
        consumed = False

        async def replay():
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {'type': 'http.request', 'body': body, 'more_body': False}

        await self.app(scope, replay, send)
