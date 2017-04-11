"""Test import expansion tool."""

from populus import Project

from ico.importexpand import expand_contract_imports


def test_expand_crowdsale_contract(project: Project):
    """Expand import statement in a Solidity source file."""

    expanded, imported_files = expand_contract_imports(project, "Crowdsale.sol")

    assert "contract Crowdsale" in expanded
    assert 'import "' not in expanded


def test_expand_token(project: Project):
    """Expand import statement in a Solidity source file, using Token contract."""

    expanded, imported_files = expand_contract_imports(project, "CrowdsaleToken.sol")
    assert "contract CrowdsaleToken" in expanded


