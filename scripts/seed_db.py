from _module_runner import run_backend_module


def seed() -> None:
    run_backend_module("app.cli.seed_db")


if __name__ == "__main__":
    seed()
