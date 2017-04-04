"""Test import expansion tool."""

from populus import Project

from ico.importexpand import expand_contract_imports


def test_expand_token(project: Project):
    """Expand import statement in a Solidity source file."""

    expanded, imported_files = expand_contract_imports(project, "Crowdsale.sol")

    assert imported_files == {'zeppelin/contracts/token/ERC20.sol', './PricingStrategy.sol', './Haltable.sol', './SafeMathLib.sol', 'zeppelin/contracts/ownership/Ownable.sol', 'Crowdsale.sol', './FinalizeAgent.sol'}

    assert "contract Crowdsale" in expanded
    assert 'import "' not in expanded

