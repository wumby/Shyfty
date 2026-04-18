from _module_runner import run_backend_module


def backfill() -> None:
    run_backend_module("app.cli.backfill_signal_features")


if __name__ == "__main__":
    backfill()
