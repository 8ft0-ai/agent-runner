from relay import RelayRouter, Request, Response


def _request(call, session="operator-1"):
    return Request(call, session, "free/nemotron", "read")


def test_two_concurrent_same_session_complete_out_of_order():
    router = RelayRouter()
    router.dispatch(_request("a"))
    router.dispatch(_request("b"))
    assert router.receive(Response("b", "second")) == ("operator-1", "second")
    assert router.receive(Response("a", "first")) == ("operator-1", "first")
    assert router.pending.outstanding() == set()


def test_three_concurrent_calls_retained():
    router = RelayRouter()
    for call in ("a", "b", "c"):
        router.dispatch(_request(call))
    assert router.pending.outstanding() == {"a", "b", "c"}


def test_request_ids_must_be_unique():
    router = RelayRouter()
    router.dispatch(_request("same"))
    try:
        router.dispatch(_request("same", "operator-2"))
        assert False, "duplicate request id was accepted"
    except ValueError:
        pass


def test_multiple_requests_do_not_overwrite_the_same_session():
    router = RelayRouter()
    for call in ("read", "edit", "bash"):
        router.dispatch(_request(call))
    assert router.receive(Response("read", "source")) == ("operator-1", "source")
    assert router.receive(Response("edit", "patched")) == ("operator-1", "patched")
    assert router.receive(Response("bash", "tests passed")) == ("operator-1", "tests passed")


def test_two_concurrent_requests_both_survive_early_completion():
    router = RelayRouter()
    router.dispatch(_request("first", "same"))
    router.dispatch(_request("second", "same"))
    assert router.pending.outstanding() == {"first", "second"}
    assert router.receive(Response("first", "done")) == ("same", "done")
    assert router.pending.outstanding() == {"second"}
