#!/usr/bin/env python3
"""Run V5 on all 346 entries and generate result file."""
import subprocess, re, sys

# Read entries
entries = []
with open("D:/University/密码学/密码数学挑战赛/result.txt", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line[0] == '#':
            continue
        m = re.match(r'@\((\d+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*([^,]+),\s*([^)]+)\)', line)
        if m:
            R = int(m.group(1))
            u = int(m.group(2), 16)
            v = int(m.group(3), 16)
            vt = float(m.group(4))
            entries.append((R, u, v, vt))

print(f"Processing {len(entries)} entries...")

PYTHON = "C:/Users/Lenovo/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SCRIPT = "D:/University/密码学/密码数学挑战赛/computecor_hull_v5.py"

results = []
for i, (R, u, v, vt) in enumerate(entries):
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{len(entries)}...")
    
    inp = f"{R}\n0x{u:08X}\n0x{v:08X}\n"
    result = subprocess.run(
        [PYTHON, SCRIPT],
        input=inp,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    try:
        ve = float(result.stdout.strip())
    except ValueError:
        ve = 0.0
        print(f"  WARN: bad output for R={R} u=0x{u:08X} v=0x{v:08X}: {result.stdout}")
    
    results.append((R, u, v, vt, ve))

# Write output
with open("D:/University/密码学/密码数学挑战赛/result_v5.txt", "w") as f:
    f.write("🔥 V5线性壳结构模型 48小时稳定扫描\n")
    for R, u, v, vt, ve in results:
        f.write(f"@({R}, 0x{u:08X}, 0x{v:08X}, {ve:.10e})\n")

print(f"\nDone! {len(results)} entries written to result_v5.txt")
