"""Every test file, run alone or together, uses a throwaway database and dev funds.

`orbit.db` reads ORBIT_DB when it is imported, so this must run before any test imports the
app. tests/test_app.py sets the same values itself; this file makes the others safe too (a
file run on its own once wrote into the real orbit.db).
"""
import os

os.environ["ORBIT_DEV"] = "1"
os.environ["ORBIT_DB"] = "test_app.db"
