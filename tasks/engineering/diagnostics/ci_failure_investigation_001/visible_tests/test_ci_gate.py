from ci_probe import select_checks


def test_client_change_isolated():
    assert select_checks(["src/api_client/transport.py"]) == ("client-unit",)


def test_worker_sibling_does_not_trigger_worker():
    assert select_checks(["src/worker-old/retries.py"]) == ()


def test_docs_backup_is_not_docs():
    assert select_checks(["docs_archive/intro.md"]) == ()


def test_combination_preserves_only_real_check_owners():
    assert select_checks(["src/api_client/x.py", "src/worker-next/task.py"]) == ("client-unit",)
