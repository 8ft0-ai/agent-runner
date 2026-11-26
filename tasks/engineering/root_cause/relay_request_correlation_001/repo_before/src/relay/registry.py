"""Pending calls awaiting tool results from an inference-only provider."""

from .models import Request, Response


class UnknownResponse(ValueError):
    pass


class PendingRegistry:
    def __init__(self) -> None:
        self._pending: dict[str, Request] = {}

    def register(self, request: Request) -> None:
        if any(existing.request_id == request.request_id
               for existing in self._pending.values()):
            raise ValueError("duplicate request_id")
        self._pending[request.session_id] = request

    def complete(self, response: Response) -> tuple[str, str]:
        """Return the originating session and result; consume only this call."""
        key = next(
            (key for key, request in self._pending.items()
             if request.request_id == response.request_id),
            None,
        )
        if key is None:
            raise UnknownResponse(response.request_id)
        request = self._pending.pop(key)
        return request.session_id, response.output

    def outstanding(self) -> set[str]:
        return {request.request_id for request in self._pending.values()}
