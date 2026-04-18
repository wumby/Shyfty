from _module_runner import run_backend_module


def backtest() -> None:
    run_backend_module("app.cli.backtest_signals")


if __name__ == "__main__":
    backtest()
