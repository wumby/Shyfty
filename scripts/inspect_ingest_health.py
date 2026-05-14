from _module_runner import run_backend_module


def run() -> None:
    run_backend_module("app.cli.inspect_ingest_health")


if __name__ == "__main__":
    run()
