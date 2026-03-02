# Qt Creator setup (ColourSorter)

## Open project
1. Open `ColourSorter.pro` in Qt Creator.
2. Use any Desktop kit (project is `TEMPLATE = aux`, no C++ build required).

## Run/Debug configurations
Create two **Custom Executable** run configs:

1. **Bench GUI**
   - Executable: `qtcreator/run_bench_gui.sh`
   - Working directory: project root
   - Environment:
     - `PYTHONPATH=src:gui`
     - `QT_QPA_PLATFORM` (optional; e.g. `xcb`, `wayland`, `offscreen`)

2. **Webcam POC**
   - Executable: `qtcreator/run_webcam_poc.sh`
   - Working directory: project root
   - Environment:
     - `PYTHONPATH=src:gui`
     - `QT_QPA_PLATFORM` (optional)

## Runtime blockers
- `libGL.so.1` is required for OpenCV webcam/Qt rendering paths.
- `pyserial` is optional; serial integration paths are disabled when missing.
