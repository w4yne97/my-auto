"""Auto-learning test fixtures and setup."""
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Early configuration hook to manage sys.path isolation.

    Both auto-reading and auto-learning manipulate sys.path at module-import time
    to work around Python's lack of dash-in-package-name imports. This early hook
    ensures each module's sys.path modifications don't pollute the global namespace
    during test collection.
    """
    # Store original sys.modules keys so we can clean up later
    config._original_modules = set(sys.modules.keys())
    config._original_path = sys.path.copy()


def pytest_unconfigure(config):
    """Cleanup hook to restore sys.path and sys.modules after all tests."""
    if hasattr(config, "_original_modules"):
        # Remove any modules imported during testing
        for mod_name in list(sys.modules.keys()):
            if mod_name not in config._original_modules:
                del sys.modules[mod_name]
    if hasattr(config, "_original_path"):
        sys.path[:] = config._original_path


@pytest.fixture(autouse=True)
def cleanup_sys_path_and_modules(request):
    """Cleanup sys.path and sys.modules after each test to prevent cross-module interference.

    Auto-reading and auto-learning both manipulate sys.path for dash-in-package-name
    workaround. When running both test suites together, we need to clean up after each
    test to prevent "models" resolution conflicts.
    """
    original_path = sys.path.copy()
    original_modules = set(sys.modules.keys())
    yield
    # Restore sys.path
    sys.path[:] = original_path
    # Remove any modules that were imported during this test
    for mod_name in list(sys.modules.keys()):
        if mod_name not in original_modules:
            del sys.modules[mod_name]
