#!/usr/bin/env python3
"""Compatibility entry point; implementation lives in pulseforge_executor.

Normal imports resolve to the same module object so patched globals, class state
and logger handlers remain shared. The historical CLI delegates without spawning
another process or changing arguments.
"""
if __name__ == "__main__":
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name("pulseforge_executor.py")), run_name="__main__")
else:
    import importlib
    from pathlib import Path
    import sys
    implementation = importlib.import_module("pulseforge_executor")
    if Path(implementation.__file__).resolve() != Path(__file__).with_name("pulseforge_executor.py").resolve():
        raise ImportError("Conflicting PulseForge executor module identity")
    sys.modules[__name__] = implementation
