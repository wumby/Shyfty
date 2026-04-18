from _module_runner import run_backend_module


def fetch() -> None:
    run_backend_module("app.cli.fetch_nba_data")


if __name__ == "__main__":
    fetch()
