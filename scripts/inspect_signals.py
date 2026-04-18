from _module_runner import run_backend_module


def inspect() -> None:
    run_backend_module("app.cli.inspect_signals")


if __name__ == "__main__":
    inspect()
