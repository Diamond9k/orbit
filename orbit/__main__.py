"""Run Orbit:  python -m orbit

Settings come from environment variables. If a file named .env sits in the folder you run
from, its KEY=value lines are loaded first, without overriding anything already set.
"""
import os
from pathlib import Path

import uvicorn


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


if __name__ == "__main__":
    load_dotenv()
    uvicorn.run("orbit.app:app", host=os.environ.get("ORBIT_HOST", "127.0.0.1"),
                port=int(os.environ.get("ORBIT_PORT", "8000")), reload=False)
