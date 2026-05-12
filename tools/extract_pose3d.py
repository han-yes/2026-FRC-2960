#!/usr/bin/env python3
"""Extract full Pose3d (x, y, z, yaw) samples from a wpilog for path analysis."""
import sys
import csv
import math
import struct
from wpiutil.log import DataLogReader


def quat_to_yaw_deg(w, x, y, z):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


def main(path, signal_substr, out_csv):
    entries = {}
    rows = []
    reader = DataLogReader(path)
    for rec in reader:
        if rec.isStart():
            info = rec.getStartData()
            entries[info.entry] = (info.name, info.type)
            continue
        if rec.isControl():
            continue
        eid = rec.getEntry()
        if eid not in entries:
            continue
        name, dtype = entries[eid]
        if signal_substr.lower() not in name.lower():
            continue
        if not dtype.startswith("struct:"):
            continue
        raw = rec.getRaw()
        if len(raw) < 56:
            continue
        x, y, z, qw, qx, qy, qz = struct.unpack_from("<7d", raw, 0)
        ts = rec.getTimestamp() / 1_000_000.0
        yaw = quat_to_yaw_deg(qw, qx, qy, qz)
        rows.append((ts, x, y, z, yaw))

    rows.sort()
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "z", "yaw_deg"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
