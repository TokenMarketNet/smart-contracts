"""Expand Solidity import statements for Etherscan verification service.

Mainly need for EtherScan verification service.
"""
import os
from typing import Tuple

from populus import Project


class Expander:
    """Solidity import expanded."""

    def __init__(self, project: Project):
        self.project = project
        self.processed_imports = set()

    def expand_file(self, import_path: str):
        """Read Solidity source code and expart any import paths inside.

        Supports Populus remapping settings:

        http://populus.readthedocs.io/en/latest/config.html#compiler-settings

        :param import_path:
        """

        # Already handled
        if import_path in self.processed_imports:
            return ""

        # TODO: properly handle import remapping here, read them from project config
        if import_path.startswith("zeppelin/"):
            abs_import_path = os.path.join(os.getcwd(), import_path)
        else:
            abs_import_path = os.path.join(os.getcwd(), "contracts", import_path)

        abs_import_path = os.path.abspath(abs_import_path)

        with open(abs_import_path, "rt") as inp:
            source = inp.read()
            self.processed_imports.add(import_path)
            return self.process_source(source)


    def process_source(self, src: str):
        """Process Solidity source code and expand any import statement."""

        out = []

        for line in src.split("\n"):
            # Detect import statements, ghetto way
            if line.startswith('import "'):
                prefix, import_path, suffix = line.split('"')
                source = self.expand_file(import_path)
                out += source.split("\n")
            else:
                out.append(line)

        return "\n".join(out)


def expand_contract_imports(project: Project, contract_filename: str) -> Tuple[str, str]:
    """Expand Solidity import statements.

    :return: Tuple[final expanded source, set of processed filenames]
    """
    exp = Expander(project)
    return exp.expand_file(contract_filename), exp.processed_imports
