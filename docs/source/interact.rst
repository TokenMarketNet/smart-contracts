=========================================
Interacting with deployed smart contracts
=========================================

.. contents:: :local:

Introduction
============

This chapter shows how one can interact with deployed smart contracts.

Interaction is easiest through a Jupyter Notebook console where you can edit and run script snippets.

.. image:: screenshots/ipython.png
    :width: 600

All snippets will connect to Ethereum node through a JSON RPC provider that has been configured in ``populus.json``.

Getting Jupyter Notebook
------------------------

Install it with `pip` in the activated Python virtual environment:

.. code-block:: console

    pip install jupyter

Then start Jupyter Notebook:

.. code-block:: console

    jupyter notebook

Releasing a token
=================

See :ref:`deploy-token` example how to deploy a crowdsale token contract that is transfer locked up by default. The crowdsale tokens cannot be transferred until the release agent makes the token transferable. As we set our owner address as the release agent we can do this from Python console.

Then copy and edit the following snippet with your address information:

.. code-block:: python

    import populus
    from populus.utils.accounts import is_account_locked
    from populus.utils.cli import request_account_unlock
    from eth_utils import from_wei
    from ico.utils import check_succesful_tx

    # Which network we deployed our contract
    chain_name = "ropsten"

    # Owner account on geth
    owner_address = "0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6"

    # Where did we deploy our token
    contract_address = "0x513a7437d355293ac92d6912d9a8b257a343fb36"

    project = populus.Project()

    with project.get_chain(chain_name) as chain:

        web3 = chain.web3
        print("Web3 provider is", web3.currentProvider)
        print("Owner address is", owner_address)
        print("Owner balance is", from_wei(web3.eth.getBalance(owner_address), "ether"), "ETH")

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, owner_address):
            request_account_unlock(chain, owner_address, None)

        transaction = {"from": owner_address}
        Contract = chain.get_contract_factory("CrowdsaleToken")

        contract = Contract(address=contract_address)
        print("Attempting to release the token transfer")
        txid = contract.transact(transaction).releaseTokenTransfer()
        check_succesful_tx(web3, txid)
        print("Token released")

Transfering tokens
==================

We have deployed a crowdsale token and made it transferable as above. Now let's transfer some tokens to our friend in Ropsten testnet.

* We create a Ropsten testnet wallet on `MyEtherWallet.com <https://myetherwallet.com/>`_ - in this example our MyEtherWallet address is 0x47FcAB60823D13B73F372b689faA9D3e8b0C48b5

* We include our deployed token contract there through *Add Custom Token* button

* Now let's transfer some tokens into this wallet through IPython console from our owner account

.. code-block:: python

    import populus
    from populus.utils.accounts import is_account_locked
    from populus.utils.cli import request_account_unlock
    from eth_utils import from_wei
    from ico.utils import check_succesful_tx

    # Which network we deployed our contract
    chain_name = "ropsten"

    # Owner account on geth
    owner_address = "0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6"

    # Where did we deploy our token
    contract_address = "0x513a7437d355293ac92d6912d9a8b257a343fb36"

    # The address where we are transfering tokens into
    buddy_address = "0x47FcAB60823D13B73F372b689faA9D3e8b0C48b5"

    # How many tokens we transfer
    amount = 1000

    project = populus.Project()

    with project.get_chain(chain_name) as chain:

        Contract = chain.get_contract_factory("CrowdsaleToken")
        contract = Contract(address=contract_address)

        web3 = chain.web3
        print("Web3 provider is", web3.currentProvider)
        print("Owner address is", owner_address)
        print("Owner balance is", from_wei(web3.eth.getBalance(owner_address), "ether"), "ETH")
        print("Owner token balance is", contract.call().balanceOf(owner_address))

        # Goes through geth account unlock process if needed
        if is_account_locked(web3, owner_address):
            request_account_unlock(chain, owner_address, None)

        transaction = {"from": owner_address}

        print("Attempting to transfer some tokens to our MyEtherWallet account")
        txid = contract.transact(transaction).transfer(buddy_address, amount)
        check_succesful_tx(web3, txid)
        print("Transfered", amount, "tokens to", buddy_address, "in transaction https://ropsten.etherscan.io/tx/{}".format(txid))

We get output like::

    Web3 provider is RPC connection http://127.0.0.1:8546
    Owner address is 0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6
    Owner balance is 1512.397773239968990885 ETH
    Owner token balance is 99000
    Attempting to transfer some tokens to our MyEtherWallet account
    Transfered 1000 tokens to 0x47FcAB60823D13B73F372b689faA9D3e8b0C48b5 in transaction https://ropsten.etherscan.io/tx/0x5460742a4f40dd573aeadedde95fc57fff6de800dde9494520c4f7852d7a956d

Etherscan transfer confirmation
-------------------------------

We can see `the transaction in the blockchain explorer <https://twitter.com/tokenmarket/status/847556407033573376>`_:

.. image:: screenshots/etherscan_token_transfer.png
    :width: 600

MyEtherWallet transfer confirmation
-----------------------------------

And then finally we see tokens in our MyEtherWallet:

.. image:: screenshots/myetherwallet_token.png
    :width: 600

Setting the actual ICO contract for a pre-ICO contract
======================================================

Example setting the ICO contract for a presale:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked

    p = populus.Project()
    account = "0xd58550a50161edf805a25431fc0bb850ff160bad"

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "PresaleFundCollector")
        contract = Contract(address="0x858759541633d5142855b27f16f5f67ea78654bf")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        txid = contract.transact({"from": account}).setCrowdsale("0xb57d88c2f70150cb688da7b1d749f1b1b4d72f4c")
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")

Example triggering the funds transfer to ICO:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked

    p = populus.Project()
    account = "0xd58550a50161edf805a25431fc0bb850ff160bad"

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "PresaleFundCollector")
        contract = Contract(address="0x858759541633d5142855b27f16f5f67ea78654bf")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        txid = contract.transact({"from": account}).parcipateCrowdsaleAll()
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")


Whitelisting crowdsale participants
===================================

Here is an example how to whitelist ICO participants before the ICO beings:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked

    p = populus.Project()
    account = "0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25"  # Our controller account on Kovan

    with p.get_chain("kovan") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "Crowdsale")
        contract = Contract(address="0x06829437859594e19276f87df601436ef55af4f2")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        txid = contract.transact({"from": account}).setEarlyParicipantWhitelist("0x65cbd9a48c366f66958196b0a2af81fc73987ba3", True)
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")


Change pricing strategy
=======================

To mix fat finger errors:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked

    p = populus.Project()
    account = "0x"  # Our controller account on Kovan

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "Crowdsale")
        contract = Contract(address="0x")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        txid = contract.transact({"from": account}).setPricingStrategy("0x")
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")


Test buy token
==============

Try to buy from a whitelisted address or on a testnet with a generated customer id:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked
    from eth_utils import to_wei

    import uuid

    p = populus.Project()
    account = "0x"  # Our controller account on Kovan

    with p.get_chain("kovan") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "Crowdsale")
        contract = Contract(address="0x")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4

        txid = contract.transact({"from": account, "value": to_wei(2, "ether")}).buyWithCustomerId(customer_id)
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")


Halt payment forwarder
======================

After a token sale is ended, stop ETH payment forwarder.

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked
    from eth_utils import to_wei

    import uuid

    p = populus.Project()
    account = "0x"  # Our controller account on Kovan

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "PaymentForwarder")
        contract = Contract(address="0x")

        if is_account_locked(web3, account):
            request_account_unlock(chain, account, None)

        customer_id = int(uuid.uuid4().hex, 16)  # Customer ids are 128-bit UUID v4

        txid = contract.transact({"from": account, "value": to_wei(2, "ether")}).buyWithCustomerId(customer_id)
        print("TXID is", txid)
        check_succesful_tx(web3, txid)
        print("OK")


Getting data field value for a function call
============================================

You can get the function signature (data field payload for a tranaction) for any smart contract function using the following:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked
    from eth_utils import to_wei

    import uuid

    p = populus.Project()
    account = "0x"  # Our controller account on Kovan

    with p.get_chain("kovan") as chain:
        web3 = chain.web3
        Contract = getattr(chain.contract_factories, "PreICOProxyBuyer")
        # contract = Contract(address="0x")

        sig_data = Contract._prepare_transaction("claimAll")
        print("Data payload is", sig_data["data"])


Set early participant pricing
=============================

Set pricing data for early investors using PresaleFundCollector + MilestonePricing contracts.

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked
    from eth_utils import to_wei, from_wei

    # The base price for which we are giving discount %
    RETAIL_PRICE = 0.0005909090909090909

    # contract, price tuples
    PREICO_TIERS = [
        # 40% bonus tier
        ("0x78c6b7f1f5259406be3bc73eca1eaa859471b9f3", to_wei(RETAIL_PRICE * 1/1.4, "ether")),

        # 35% tier A
        ("0x6022c6c5de7c4ab22b070c36c3d5763669777f68", to_wei(RETAIL_PRICE * 1/1.35, "ether")),

        # 35% tier B
        ("0xd3fa03c67cfba062325cb6f4f4b5c1e642f1cffe", to_wei(RETAIL_PRICE * 1/1.35, "ether")),

        # 35% tier C
        ("0x9259b4e90c5980ad2cb16d685254c859f5eddde5", to_wei(RETAIL_PRICE * 1/1.35, "ether")),

        # 25% tier
        ("0xee3dfe33e53deb5256f31f63a59cffd14c94019d", to_wei(RETAIL_PRICE * 1/1.25, "ether")),

        # 25% tier B
        ("0x2d3a6cf3172f967834b59709a12d8b415465bb4c", to_wei(RETAIL_PRICE * 1/1.25, "ether")),

        # 25% tier C
        ("0x70b0505c0653e0fed13d2f0924ad63cdf39edefe", to_wei(RETAIL_PRICE * 1/1.25, "ether")),

        # 25% tier D
        ("0x7cfe55c0084bac03170ddf5da070aa455ca1b97d", to_wei(RETAIL_PRICE * 1/1.25, "ether")),
    ]

    p = populus.Project()
    deploy_address = "0xe6b645a707005bb4086fa1e366fb82d59256f225"  # Our controller account on mainnet
    pricing_strategy_address  = "0x9321a0297cde2f181926e9e6ac5c4f1d97c8f9d0"
    crowdsale_address = "0xaa817e98ef1afd4946894c4476c1d01382c154e1"

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3

        # Safety check that Crodsale is using our pricing strategy
        Crowdsale = chain.contract_factories.Crowdsale
        crowdsale = Crowdsale(address=crowdsale_address)
        assert crowdsale.call().pricingStrategy() == pricing_strategy_address

        # Get owner access to pricing
        MilestonePricing = chain.contract_factories.MilestonePricing
        pricing_strategy = MilestonePricing(address=pricing_strategy_address)

        PresaleFundCollector = chain.contract_factories.PresaleFundCollector
        for preico_address, price_wei_per_token in PREICO_TIERS:

            eth_price = from_wei(price_wei_per_token, "ether")
            tokens_per_eth = 1 / eth_price
            print("Tier", preico_address, "price per token", eth_price, "tokens per eth", round(tokens_per_eth, 2))

            # Check presale contract is valid
            presale = PresaleFundCollector(address=preico_address)
            assert presale.call().investorCount() > 0, "No investors on contract {}".format(preico_address)

            txid = pricing_strategy.transact({"from": deploy_address}).setPreicoAddress(preico_address, price_wei_per_token)
            print("TX is", txid)
            check_succesful_tx(web3, txid)

Move early participant funds to crowdsale
=========================================

Move early participant funds from PresaleFundCollector to crowdsale.

Example:

.. code-block:: python

    from ico.utils import check_succesful_tx
    import populus
    from populus.utils.cli import request_account_unlock
    from populus.utils.accounts import is_account_locked
    from eth_utils import to_wei, from_wei
    from ico.earlypresale import participate_early

    presale_addresses = [
        "0x78c6b7f1f5259406be3bc73eca1eaa859471b9f3",
        "0x6022c6c5de7c4ab22b070c36c3d5763669777f68",
        "0xd3fa03c67cfba062325cb6f4f4b5c1e642f1cffe",
        "0x9259b4e90c5980ad2cb16d685254c859f5eddde5",
        "0xee3dfe33e53deb5256f31f63a59cffd14c94019d",
        "0x2d3a6cf3172f967834b59709a12d8b415465bb4c",
        "0x70b0505c0653e0fed13d2f0924ad63cdf39edefe",
        "0x7cfe55c0084bac03170ddf5da070aa455ca1b97d",
    ]

    p = populus.Project()
    deploy_address = "0x"  # Our controller account on mainnet
    pricing_strategy_address = "0x"
    crowdsale_address = "0x"

    with p.get_chain("mainnet") as chain:
        web3 = chain.web3

        Crowdsale = chain.contract_factories.Crowdsale
        crowdsale = Crowdsale(address=crowdsale_address)

        for presale_address in presale_addresses:
            print("Processing contract", presale_address)
            participate_early(chain, web3, presale_address, crowdsale_address, deploy_address, timeout=3600)
            print("Crowdsale collected", crowdsale.call().weiRaised() / 10**18, "tokens sold", crowdsale.call().tokensSold() / 10**8, "money left", from_wei(web3.eth.getBalance(deploy_address), "ether"))

