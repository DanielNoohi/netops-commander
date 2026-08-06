"""Optional dependency detection."""
import importlib
import shutil
import subprocess
from ..utils.logger import get_logger

log = get_logger(__name__)


def _check_cli(command: list, timeout: int = 3) -> bool:
    """Check if a CLI tool is available (with timeout)."""
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        return True
    except Exception:
        return False


def _check_module(name: str) -> bool:
    """Check if a Python module is importable (fast, no subprocess)."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def get_optional_dependencies() -> dict:
    """Check all optional dependencies. Fast — no subprocesses for Python packages."""
    return {
        "nmap": _check_cli(["nmap", "--version"]),
        "scapy": _check_module("scapy"),
        "pysnmp": _check_module("pysnmp"),
        "putty": shutil.which("putty") is not None,
        "winscp": shutil.which("winscp") is not None,
        "powershell": shutil.which("powershell") is not None or shutil.which("pwsh") is not None,
    }
