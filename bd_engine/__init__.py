# BD Engine - Nutraceutical Talent Acquisition Business Development Engine
import os
from pathlib import Path

# Auto-load .env from workspace root if present
_env_file = Path(__file__).resolve().parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path.cwd() / ".env"

if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip("'\"")
                if _k and not os.environ.get(_k):
                    os.environ[_k] = _v

