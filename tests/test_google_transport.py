"""Only google/transport.py may open sockets (spec 004 T003)."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "alfabeta"
NETWORK = {"urllib.request", "http.client", "socket", "urllib.error"}


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_positive_control_transport_imports_urllib():
    assert "urllib.request" in _imports(SRC / "google" / "transport.py")


def test_no_other_module_opens_sockets():
    files = [p for p in SRC.rglob("*.py") if p.name != "transport.py"]
    assert len(files) >= 6, "the sweep found too few modules to mean anything"
    offenders = {str(p.relative_to(SRC)): sorted(_imports(p) & NETWORK) for p in files if _imports(p) & NETWORK}
    assert offenders == {}
