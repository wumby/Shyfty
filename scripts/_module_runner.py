import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
BACKEND_VENV_PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"


def run_backend_module(module_name: str) -> None:
    active_venv = Path(os.environ["VIRTUAL_ENV"]).resolve() if os.environ.get("VIRTUAL_ENV") else None
    expected_venv = BACKEND_VENV_PYTHON.parent.parent.resolve()
    if BACKEND_VENV_PYTHON.exists() and active_venv != expected_venv:
        env = os.environ.copy()
        existing_python_path = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{BACKEND_ROOT}{os.pathsep}{existing_python_path}" if existing_python_path else str(BACKEND_ROOT)
        )
        os.execve(
            str(BACKEND_VENV_PYTHON),
            [str(BACKEND_VENV_PYTHON), "-m", module_name, *sys.argv[1:]],
            env,
        )
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    runpy.run_module(module_name, run_name="__main__")
