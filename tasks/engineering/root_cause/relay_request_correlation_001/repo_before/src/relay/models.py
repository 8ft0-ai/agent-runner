"""Provider-neutral request/response values for the simulated relay."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    request_id: str
    session_id: str
    model: str
    prompt: str


@dataclass(frozen=True)
class Response:
    request_id: str
    output: str
