"""Deploy crowdsale token and smart contract in testnet.

A simple Python script to deploy contracts and then do a smoke test for them.
"""
from eth_utils import to_wei
from populus import Project
from populus.utils.cli import get_unlocked_default_account_address
from populus.utils.wait import wait_for_transaction_receipt
from web3 import RPCProvider
from web3 import Web3


def check_succesful_tx(web3: Web3, txid: str, timeout=180) -> dict:
    """See if transaction went through (Solidity code did not throw).

    :return: Transaction receipt
    """

    # http://ethereum.stackexchange.com/q/6007/620
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)

    # EVM has only one error mode and it's consume all gas
    assert txinfo["gas"] != receipt["gasUsed"]
    return receipt


def main():

    project = Project()

    # This is configured in populus.json
    # We are working on a testnet
    chain_name = "local"
    print("Make sure {} chain is running, you can connect to it, or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:

        web3 = Web3(RPCProvider())
        print("Web3 provider is", web3.currentProvider)

        # Load Populus contract proxy classes
        Crowdsale = chain.get_contract_factory('Crowdsale')
        Token = chain.get_contract_factory('crowdsaleToken')

        # The address who will be the owner of the contracts
        beneficiary = web3.eth.coinbase
        assert beneficiary, "Make sure your node has coinbase account created"

        # Generated account on local geth
        multisig_address = "0x6bcf2b956e6bb630954a7ffc7c6f42c0f60dfd80"

        # One generated account on local geth
        # MUST be unlocked
        customer = "0xc0addfc55b27886eb6c31a2a881b8ca979082b77"

        # Goes through coinbase account unlock process if needed
        get_unlocked_default_account_address(chain)

        # Deploy crowdsale, open since 1970
        txhash = Crowdsale.deploy(transaction={"from": beneficiary}, args=[beneficiary, multisig_address, 1])
        print("Deploying crowdsale, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        crowdsale_address = receipt["contractAddress"]
        print("Crowdsale contract address is", crowdsale_address)

        # Deploy token
        txhash = Token.deploy(transaction={"from": beneficiary}, args=[beneficiary])
        print("Deploying token, tx hash is", txhash)
        receipt = check_succesful_tx(web3, txhash)
        token_address = receipt["contractAddress"]
        print("Token contract address is", token_address)

        # Make contracts aware of each other
        print("Initializing contracts")
        crowdsale = Crowdsale(address=crowdsale_address)
        token = Token(address=token_address)
        txhash = crowdsale.transact({"from": beneficiary}).setToken(token_address)
        check_succesful_tx(web3, txhash)

        # Set the crowdfund approval limit
        txid = token.transact({"from": beneficiary}).approve(crowdsale.address, 440000000)
        check_succesful_tx(web3, txid)
        token.call().allowance(beneficiary, crowdsale.address) == 440000000

        # Give the customer some money
        print("Funding customer")
        txid = web3.eth.sendTransaction({
            "from": web3.eth.coinbase,
            "to": customer,
            "value": to_wei(30, "ether"),
        })
        check_succesful_tx(web3, txid)

        # Make one buy
        print("Making one crowdsale purchase")
        txid = web3.eth.sendTransaction({
            "from": customer,
            "to": crowdsale.address,
            "value": to_wei(20, "ether"),
            "gas": 250000,
        })
        check_succesful_tx(web3, txid)

        # Do some contract reads to see everything looks ok
        print("Token total supply is", token.call().totalSupply())
        print("Crowdsale max goal is", crowdsale.call().maxGoal())
        print("Customer has token balance", token.call().balanceOf(customer))
        print("Tokens sold", crowdsale.call().tokensSold())
        print("Multisig address is", multisig_address)
        print("Multisig balance is", web3.eth.getBalance(multisig_address))
        print("Customer has crowdsale WEI balance", crowdsale.call().balanceOf(customer))

        print("All done! Enjoy your decentralized future.")


if __name__ == "__main__":
    main()
