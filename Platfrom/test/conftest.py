"""
Test-level conftest — ensures the project root is on sys.path so that
tests in subdirectories (e.g., ``test/sandbox/``) can resolve imports
like ``from sandbox.order_manager import OrderManager``.

The root ``conftest.py`` at ``Platfrom/conftest.py`` also does this,
but pytest may not always discover it when running individual test
subdirectories.  This conftest provides a belt-and-suspenders approach.
"""

import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
