from ci_probe import select_checks


def test_client_only_change_does_not_run_api_contract():
    assert select_checks(["src/api_client/transport.py"]) == ("client-unit",)


def test_worker_backup_directory_is_not_a_worker_change():
    assert select_checks(["src/worker_backup/index.py"]) == ()
