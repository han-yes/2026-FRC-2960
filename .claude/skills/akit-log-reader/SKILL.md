---
name: akit-log-reader
description: Read and verify the most recent AdvantageKit simulation log. Confirms the correct autonomous paths ran, the robot actually moved, and the P2PC path configuration matches expectations. Use after a simulation run to validate auton behavior, or any time the user asks to inspect/verify the latest akit log.
---

# AdvantageKit Log Reader

Read the most recent simulation log and verify that the autonomous routine ran correctly — specifically that the robot moved along the expected P2PC paths.

## Environment

- **Python**: `C:\Users\hangy\AppData\Local\Python\bin\python.exe`
- **Log parser**: `tools\parse_wpilog.py` (in project root)
- **Logs folder**: `logs\` (in project root)
- **Project root**: `C:\Users\hangy\Documents\2026-FRC-2960-1`

## Step 1 — Find the log file

The simulation output contains a line like:
```
[AdvantageKit] Renaming log to "logs\akit_26-05-07_17-51-04.wpilog"
```

If you have the simulation shell output, extract the log path from that line. Otherwise, find the newest `.wpilog` in `logs\`:

```powershell
Get-ChildItem "C:\Users\hangy\Documents\2026-FRC-2960-1\logs\*.wpilog" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
```

## Step 2 — Confirm autonomous ran

Check that the robot was enabled in autonomous mode:

```powershell
& "C:\Users\hangy\AppData\Local\Python\bin\python.exe" tools\parse_wpilog.py <logfile> --signals DriverStation/Autonomous DriverStation/Enabled
```

Look for:
- `/DriverStation/Enabled` switching to `1`
- `/DriverStation/Autonomous` switching to `1`

If neither goes to `1`, autonomous never ran — stop and report that.

## Step 3 — Read P2PC path configuration (informational)

Check what paths were configured in the log:

```powershell
& "C:\Users\hangy\AppData\Local\Python\bin\python.exe" tools\parse_wpilog.py <logfile> --signals "P2PC" "P2P Auton"
```

Key signals to report:
| Signal | Meaning |
|---|---|
| `/NetworkInputs/SmartDashboard/Intake Path P2PC 0` | First intake path name |
| `/NetworkInputs/SmartDashboard/Neutral Zone P2PC 0` | Neutral zone waypoint |
| `/NetworkInputs/SmartDashboard/Return Type P2PC 0` | Return path type |
| `/NetworkInputs/SmartDashboard/End Type P2PC 0` | End behavior |
| `/NetworkInputs/SmartDashboard/Repeat Cycle P2PC 0` | Whether cycle repeats |
| `/NetworkInputs/SmartDashboard/Start Type P2PC` | Starting position type |

Report each configured path/setting as a bullet list.

> **CLAUDESIM note:** When `currentMode == RobotMode.CLAUDESIM` (set in `Robot.java`), `autonomousInit()` overrides the chooser-selected command with `robotContainer.getP2PClaudeAutonCmd()` (a hard-coded preset). In that mode the P2PC chooser values are **informational only** — `None` here is expected and is not a failure. Verify the preset signature in Step 5b instead.

## Step 4 — Verify robot movement via MapleSim Pose3d

The ground-truth pose during simulation is the `MapleSim Pose3d` signal (struct:Pose3d). Extract it:

```powershell
& "C:\Users\hangy\AppData\Local\Python\bin\python.exe" tools\parse_wpilog.py <logfile> --signals "MapleSim Pose3d" --out C:\Temp\pose.csv
```

Then check the CSV for movement: the X and Y values (first two doubles in the struct, decoded as the first double) should change over time. If the pose is constant throughout autonomous, the robot did not move.

> **Note:** `parse_wpilog.py` decodes structs by extracting the first `double` (little-endian) from the raw bytes. For `Pose3d` this gives the X component in meters. A changing X value confirms lateral movement.

## Step 5 — Check drivetrain command activity

```powershell
& "C:\Users\hangy\AppData\Local\Python\bin\python.exe" tools\parse_wpilog.py <logfile> --signals "CommandSwerveDrivetrain/CommandString" "CommandSwerveDrivetrain/ChassisSpeeds"
```

Look for:
- `CommandString` changing from `null`/idle to an actual command name — confirms a path command ran
- `ChassisSpeeds` non-zero values — confirms the drivetrain was actually driven

## Step 5b — Verify CLAUDESIM preset auton signature

If the sim was run in CLAUDESIM mode, the scheduled command is `getClaudeTestAuton(false)` from `PointToPointAutons.java`. That auton is a `SequentialCommandGroup` of:

1. `drivetrain.getResetPoseAllianceCmd(AutonWaypoints.rightTrenchAutonStart)` — pose teleport to ~`blueTrenchRight` with 90° heading
2. `getTrenchNeutralZone(false, false)` — drive through trench → neutral zone
3. `getSnakeIntakePath(false, ReturnType.BUMP)` — snake intake path
4. `getReturnBumperRoutine(false)` — return along the bump
5. `getShootRoutine(4)` — 4-second shoot routine (skipped in sim — see note)

> **Shooter-in-sim caveat:** The `ShooterWheel` subsystem does not support simulation, so the shoot stage produces no shooter velocity even when scheduled. Do **not** use `ShooterWheel/TargetVelocity` as evidence the auton completed — it will be 0 in every sim run regardless.

Run both checks below.

### 5b.1 — Starting pose matches the reset target

`getResetPoseAllianceCmd(rightTrenchAutonStart)` runs instantaneously *before* the first MapleSim log sample, so there is no in-log "jump" to detect. Instead, confirm the first logged `MapleSim Pose3d` X is near the trench start (≈ 4.5–5.0 m for a blue-alliance reset; the exact target is `FieldLayout.Trench.blueTrenchRight` minus hub offsets in `FieldLayout.java`).

```powershell
$csv = Import-Csv C:\Temp\pose.csv
"First logged X: $([math]::Round([double]$csv[0].value, 3)) m @ t=$($csv[0].timestamp)"
```

PASS if first X is in the ~4–6 m range (matches a trench-start reset). FAIL if first X is near 0 m or matches a different starting waypoint — that means the reset command didn't run.

### 5b.2 — Total path length > 2 m

`getClaudeTestAuton` covers trench → neutral zone → snake → return. Over a 20-s auton the X range (max-min) should be > 2 m. If `Max X - Min X < 1 m`, the drivetrain stalled mid-path.

## Step 6 — Report

Structure your response as:

### Autonomous Verification Report
- **Log file**: `logs\akit_<timestamp>.wpilog`
- **Auton enabled**: Yes / No
- **Robot moved**: Yes / No (based on MapleSim Pose3d X change)

### P2PC Configuration (informational in CLAUDESIM)
- Start type: ...
- Cycle 0: intake path `X` → neutral zone `Y` → return type `Z` → end type `W`
- Cycle 1: (if present)
- Repeat: Yes / No

### Drivetrain Activity
- Commands observed: (list unique CommandString values)
- Peak chassis speed: X m/s

### CLAUDESIM Preset Signature (Step 5b)
- Starting pose matches trench reset target: Yes / No (first logged X in ~4–6 m range)
- Total path length: `Max X - Min X = ... m` (expect > 2 m)

### Pass / Fail
**In CLAUDESIM mode**, PASS requires all of:
- Auton enabled (Step 2)
- Starting pose matches reset target (5b.1)
- Total path length > 2 m (5b.2)

Otherwise FAIL — name which check missed. Chooser values from Step 3 are ignored for the verdict. The shoot stage is intentionally not scored because `ShooterWheel` has no sim implementation.

**In non-CLAUDESIM sim**, PASS requires: auton enabled + robot moved + at least one drive command active. Chooser values in Step 3 should match what the user intended.

## Common issues

| Symptom | Likely cause |
|---|---|
| Robot doesn't move | `autonTypeChooser` still set to NONE — check `simulationInit()` |
| Auton never enabled | `DriverStationSim.notifyNewData()` didn't propagate — DS state lag |
| All pose values identical | `FRC_AUTON_HEADLESS` env var not set — Gradle property missing |
| Wrong paths | SmartDashboard chooser values not set before auton started |
