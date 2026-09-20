"""Network Topology Simulator Backend Package"""
import sys
import os
import types

# Register 'app' as a virtual package alias for netspout/bin
# Enables both `import models` and `import app.models` without filesystem symlinks
if 'app' not in sys.modules:
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    _app_pkg = types.ModuleType('app')
    _app_pkg.__path__ = [_pkg_dir]
    _app_pkg.__file__ = os.path.abspath(__file__)
    sys.modules['app'] = _app_pkg
