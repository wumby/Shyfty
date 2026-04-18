from _module_runner import run_backend_module


def run() -> None:
    run_backend_module("app.cli.generate_signals")


if __name__ == "__main__":
    run()
