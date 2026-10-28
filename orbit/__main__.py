"""Run Orbit:  python -m orbit"""
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("orbit.app:app", host=os.environ.get("ORBIT_HOST", "127.0.0.1"),
                port=int(os.environ.get("ORBIT_PORT", "8000")), reload=False)
