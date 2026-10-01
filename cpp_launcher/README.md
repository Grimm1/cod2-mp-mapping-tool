# Native C++ launcher

This Windows launcher checks for Python 3 and verifies that `PyQt6` and `psutil`
can be imported by the same interpreter used to run `main.py`. If either package
is missing, it asks before installing both with pip.

## Build

Install CMake and a C++17 compiler, then run these commands from this folder:

```powershell
cmake -S . -B build
cmake --build build --config Release
```

The resulting `cod2_mapping_launcher.exe` is under `build/Release` with Visual
Studio, or directly under `build` with a single-configuration generator. It
searches its parent directories for `main.py`, so keep the executable inside
this project folder or its build folder. Distribute the launcher alongside the
Python application files.

By default, the launcher uses Windows dialogs and does not open a command
window. To open a diagnostic console and see Python or pip output, start it with
the `--console` argument.