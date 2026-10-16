import asyncio
import json
from typing import AsyncGenerator
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request


class MockAiStreamService:
    """Simulates an asynchronous streaming model provider e.g.(OpenAI/Antropic)"""

    @staticmethod
    async def stream_tokens(prompt: str) -> AsyncGenerator[str, None]:
        simulate_response = f"Enchoing semantic stream for '{prompt}'"
        for token in simulate_response.split():
            await asyncio.sleep(0.08) #Non-blocking network I/O wait
            yield json.dumps({"token": token}) + "\n"

class DocumentAiStreamView(APIView):
    """
    Asynchronous endpoint for django.
    Streams AI token over Sent-Events (SSE) or raw ndjson.
    """

    permission_classes = [IsAuthenticated]

    async def get(self, request: Request) -> StreamingHttpResponse:
        #Non-blocking permission and query check would occur here via sync_to_async
        prompt = request.query_params.get("q", "Summarize document")

        #Generator yielding chunk without blocking the worker thread
        async def response_stream() -> AsyncGenerator[str, None]:
            async for token in MockAiStreamService.stream_tokens(prompt):
                yield token

        #StreamingHttpResponse with EventStream or NDJSON
        response = StreamingHttpResponse(
            response_stream(),
            content_type="application/x-ndjson"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no" #prevents Nginx form buffering the chunks
        return response