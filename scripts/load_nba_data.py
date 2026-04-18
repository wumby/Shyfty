from _module_runner import run_backend_module


def load() -> None:
    run_backend_module("app.cli.load_nba_data")


if __name__ == "__main__":
    load()
