from catalog import Catalog, Source


def test_changed_bytes_with_the_same_stamp_and_length():
    catalog = Catalog()
    catalog.refresh({"one": Source(1, b"A|1")})
    assert catalog.refresh({"one": Source(1, b"A|2")}) == {"A": 2}


def test_removed_source_disappears():
    catalog = Catalog()
    catalog.refresh({"one": Source(1, b"A|1"), "two": Source(2, b"B|1")})
    assert catalog.refresh({"one": Source(1, b"A|1")}) == {"A": 1}


def test_failed_refresh_leaves_the_previous_view():
    catalog = Catalog()
    catalog.refresh({"one": Source(1, b"A|1")})
    try:
        catalog.refresh({"one": Source(2, b"A|2"), "bad": Source(1, b"malformed")})
    except ValueError:
        pass
    else:
        raise AssertionError("expected a parse failure")
    assert catalog.view() == {"A": 1}
