#!/usr/bin/env python3
"""Generate input for V5 and run it."""
import re

# Read entries from result.txt
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
            entries.append((R, u, v))

print(f"Total entries: {len(entries)}")

# Write input file
with open("D:/University/密码学/密码数学挑战赛/_v5_input.txt", "w") as f:
    for R, u, v in entries:
        f.write(f"{R}\n0x{u:08X}\n0x{v:08X}\n")

print("Input written to _v5_input.txt")
