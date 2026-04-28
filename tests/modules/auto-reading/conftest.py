"""Re-export fixtures from tests/lib/conftest.py so module-level tests can use them."""
from tests.lib.conftest import config_path, mock_cli, output_path  # noqa: F401
