import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS_FILE = ROOT / "configs.json"
VALIDATE_SNIPPET = (
    "import sys; sys.exit(0 if sys.version_info >= (3, 13) "
    "and 'free-threading' not in sys.version else 1)"
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if sys.platform == "win32" and reconfigure is not None:
        reconfigure(encoding="oem", errors="replace")
    if not CONFIGS_FILE.is_file():
        fail(f'configs.json not found at "{CONFIGS_FILE}".')
    try:
        configs = json.loads(CONFIGS_FILE.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        fail(f"configs.json could not be parsed: {exc}")
        return
    python_path = str(configs.get("pythonPath") or "").strip()
    if not python_path:
        if sys.version_info < (3, 13) or "free-threading" in sys.version:
            fail(
                f'Auto-detected Python "{sys.executable}" is not Python 3.13+ '
                "(or is a free-threaded build, which PySide6 does not support). "
                'Set "pythonPath" in configs.json to a valid python.exe.'
            )
        print(sys.executable)
        return
    candidate = Path(python_path)
    if not candidate.is_file():
        fail(
            f'pythonPath "{python_path}" does not exist. Fix it or set it to "" for auto-detection.'
        )
    try:
        result = subprocess.run([str(candidate), "-c", VALIDATE_SNIPPET], capture_output=True)
    except OSError as exc:
        fail(f'pythonPath "{python_path}" could not be executed: {exc}')
        return
    if result.returncode != 0:
        fail(
            f'pythonPath "{python_path}" is not Python 3.13+ '
            "(or is a free-threaded build, which PySide6 does not support)."
        )
    print(str(candidate))


if __name__ == "__main__":
    main()
