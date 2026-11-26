import unittest

from relay import RelayRouter, Request, Response, UnknownResponse


def req(number, session="s-1", model="free/nemotron"):
    return Request(f"call-{number}", session, model, f"prompt {number}")


class TestRelayRouter(unittest.TestCase):
    def test_single_session_keeps_both_pending_calls(self):
        router = RelayRouter()
        router.dispatch(req(1))
        router.dispatch(req(2))
        self.assertEqual(router.pending.outstanding(), {"call-1", "call-2"})

    def test_response_for_first_pending_is_delivered(self):
        router = RelayRouter()
        router.dispatch(req(1))
        router.dispatch(req(2))
        self.assertEqual(router.receive(Response("call-1", "one")), ("s-1", "one"))
        self.assertEqual(router.receive(Response("call-2", "two")), ("s-1", "two"))
