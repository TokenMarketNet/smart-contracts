import os

import pytest


@pytest.fixture
def example_yaml_filename() -> str:
    """Example yml definition file."""
    return os.path.join(os.getcwd(), "crowdsales", "unit-test.yml")
