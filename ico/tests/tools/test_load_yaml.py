"""YAML crowdsale definition loader."""

import os
from pprint import pprint

from populus import Project

from ico.definition import load_crowdsale_definitions


def test_load_yaml(example_yaml_filename):
    """Load and expand YAML crowdsale defitions."""
    defs = load_crowdsale_definitions(example_yaml_filename, "ropsten")
    pprint(defs)
