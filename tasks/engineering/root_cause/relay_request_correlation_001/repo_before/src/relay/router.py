"""Consumer-side dispatch for one or more OpenCode sessions."""

from .models import Request, Response
from .policy import require_allowed
from .registry import PendingRegistry


class RelayRouter:
    def __init__(self) -> None:
        self.pending = PendingRegistry()

    def dispatch(self, request: Request) -> None:
        require_allowed(request.model)
        self.pending.register(request)

    def receive(self, response: Response) -> tuple[str, str]:
        return self.pending.complete(response)
