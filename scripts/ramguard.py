"""Run a command, kill it if system RAM use goes above a limit (default 90%). Windows, no deps.
Usage: python scripts/ramguard.py [--max 90] -- <cmd> [args...]"""
import ctypes, subprocess, sys, time


class MEM(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
               [(n, ctypes.c_ulonglong) for n in ("tp", "ap", "tf", "af", "tv", "av", "ave")]


def load():
    m = MEM(); m.dwLength = ctypes.sizeof(MEM)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.dwMemoryLoad


args = sys.argv[1:]
lim = 90
if args[:1] == ["--max"]:
    lim, args = int(args[1]), args[2:]
if args[:1] == ["--"]:
    args = args[1:]
if load() >= lim:
    print(f"RAMGUARD: RAM already at {load()}%, not starting", flush=True); sys.exit(3)
p = subprocess.Popen(args)
peak = 0
while p.poll() is None:
    peak = max(peak, load())
    if peak >= lim:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        print(f"RAMGUARD: killed at {peak}% RAM", flush=True); sys.exit(2)
    time.sleep(0.3)
print(f"RAMGUARD: done, peak RAM {peak}%", flush=True)
sys.exit(p.returncode)
