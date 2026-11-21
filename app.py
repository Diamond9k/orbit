"""Entry point for the public sandbox on Vercel.

Vercel looks for an `app` in this file. The address it serves is the sandbox and nothing
else: guests, test funds and simulated machines (see orbit/sandbox.py). The database is a
throwaway file, because a Vercel function can write only to /tmp and loses it on restart.

To run the real broker, use `python -m orbit` on a machine you control. See README.md.
"""
import os

os.environ["ORBIT_SANDBOX"] = "1"
os.environ["ORBIT_DB"] = "/tmp/orbit-sandbox.db"
os.environ.pop("ORBIT_DEV", None)

from orbit.app import app  # noqa: E402  (the settings above must be in place before this import)

__all__ = ["app"]
