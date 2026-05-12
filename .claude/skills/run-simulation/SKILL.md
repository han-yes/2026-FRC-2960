---
name: run-simulation
description: Run the FRC robot simulation (interactive debug, headless autonomous, or unit tests) and report build/runtime results. Use when the user asks to run the sim, test robot code without hardware, validate an autonomous routine, or debug subsystem behavior in simulation.
---

# Run FRC Simulation

Execute the WPILib robot simulation for this project and report results. Pick a mode based on the user's intent.

## Modes

### 1. Interactive Debug (default — has GUI, suspends for debugger)

**Always use this command — never `./gradlew simulateJava` directly.**

```powershell
${env:HALSIM_EXTENSIONS}=''; ${env:PATH}='C:\Users\hangy\Documents\2026-FRC-2960-1\build\jni\release;C:\WINDOWS\system32\'; & 'C:\Users\Public\wpilib\2026\jdk\bin\java.exe' '-agentlib:jdwp=transport=dt_socket,server=n,suspend=y,address=localhost:53338' '@C:\Users\hangy\AppData\Local\Temp\cp_474xt8gszb03h61i7w6cr8enr.argfile' 'frc.robot.Main'
```

- Run in background — it suspends until a debugger attaches on port 53338.
- Verify the argfile exists in `AppData\Local\Temp` before running. If it doesn't, run `.\gradlew.bat build` first to regenerate it (the argfile name may change — list the directory to find the current one).

### 2. Headless Autonomous (no GUI, auto-enabled)

Setup is already applied in this project (`build.gradle` GUI suppression + `Robot.simulationInit()` DS auto-enable). Run:

```powershell
.\gradlew.bat simulateJavaRelease -PheadlessAuton
```

- Run in background — the sim runs indefinitely.
- Stop with: `Stop-Process -Name "java" -Force` (exit code 255 is expected, not a failure).
- To restore the GUI on this task: `.\gradlew.bat simulateJavaRelease -PenableSimGui`.

### 3. Unit Tests (deterministic, CI-friendly)

```powershell
.\gradlew.bat test
```

For new tests, use `SimHooks.pauseTiming()` / `stepTiming(0.02)` and `DriverStationSim.setAutonomous(true)` / `setEnabled(true)` + `notifyNewData()`. Remember `notifyNewData()` is async (~20 ms lag) — `Timer.delay(0.100)` if you read DS state immediately after.

## Workflow

1. **Pre-flight** — confirm you're in the project root (contains `gradlew.bat` and `build.gradle`). If the user just edited code, glance at the modified files for obvious compile issues.
2. **Run** the chosen mode (background where indicated).
3. **Report** build phase vs. runtime output separately. Flag `BUILD FAILED` with the offending file/line. Surface Java exceptions and stack traces. Note WPILib-specific warnings (HAL errors, missing sim devices).
4. **Pass criteria** — look for both:
   - `********** Robot program startup complete **********`
   - `[PathPlanner] PathfindingCommand finished warmup`
5. **Ignore these expected warnings** — they appear on every clean run:
   - `Joystick Button X on port Y not available` (no DS in sim)
   - Loop overrun on the **first tick only** (JIT warmup)
   - `CameraSim.periodic(): 0.04xs` on first loop
   - `PhotonPoseEstimator` deprecation warning
6. **Real performance issue** — loop overruns after `startup complete` line.

## Post-run log analysis

Every sim writes an AdvantageKit log to `logs/akit_<timestamp>.wpilog`. To inspect:

```bash
SIMLOG=$(ls -t logs/akit_*.wpilog | head -1)
python tools/parse_wpilog.py "$SIMLOG" --catalog
python tools/parse_wpilog.py "$SIMLOG" --anomalies \
    --signals ShooterWheel Indexer IntakeAngle IntakeRoller CommandSwerveDrivetrain SystemStats
```

Missing subsystem signals under `/RealOutputs/` → that subsystem likely threw during `periodic()`.

## Error triage

- **Build error** — parse the failure, point at the file/line, suggest a fix. Common causes: missing vendor dep JSON in `vendordeps/`, WPILib version mismatch in `build.gradle`, Java syntax/import issue.
- **Runtime crash** — identify exception, map stack frames to user code vs. WPILib internals, suggest the next debug step (e.g. inspect SimDeviceSim wiring, HALSim extensions).
- **Sim runs but behavior is wrong** — pull the matching subsystem signals from the latest akit log (see above) before guessing.

## Output format

Keep responses tight. Structure:
1. **Action** — command + directory.
2. **Build result** — pass/fail + relevant snippet.
3. **Simulation status** — running / waiting for debugger / crashed.
4. **Issues** (if any) — short, with concrete fix.
5. **Next steps** — what to do now (attach debugger, open dashboard, stop the sim, etc.).
