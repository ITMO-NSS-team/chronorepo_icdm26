"""ChronoRepo demo application (ICDM 2026).

Importing the package puts experiments/ on sys.path (see config), so every
submodule can `import chrono` / `import night_lab` — the demo runs the
experiment library itself rather than a copy of it.
"""
from . import config  # noqa: F401
