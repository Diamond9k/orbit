"""Run the Orbit host program so a test can stop it cleanly.

A background thread watches for the stop file named on the command line. When it appears the
main thread gets a KeyboardInterrupt, the host program's own finally-block stops the model
server it started, and the process exits. From Orbit's side the heartbeats simply stop, which
is what a host that vanished looks like. No process is killed from outside.

    python docs/evidence/e2e_host_wrapper.py <stop file>
"""
import _thread
import os
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "host"))
import orbit_host  # noqa: E402

STOP = sys.argv[1]


def watch():
    while not os.path.exists(STOP):
        time.sleep(0.5)
    _thread.interrupt_main()


threading.Thread(target=watch, daemon=True).start()
try:
    orbit_host.main()
except KeyboardInterrupt:
    print("host program stopped by the test")
