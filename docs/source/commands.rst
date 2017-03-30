Usage
=====

presale - deploy a presale contract
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A presale contract is a contract to collect presale investor money to be moved to a crowdsale when the crowdsale opens. The cresale contract can be deployed through ``presale`` command. After deploying the investors can call its ``invest()`` and ``refund()`` function from any Ethereum wallet allowing the transaction ``data`` field set.

``presale --help``::

    Usage: presale [OPTIONS]

    Options:
      --chain TEXT     On which chain to deploy
      --address TEXT   Account to deploy from (must exist on geth)
      --days INTEGER   How many days presale is frozen for
      --minimum FLOAT  What is the minimum pre-ico buy in (ether)
      --help           Show this message and exit.

Example that makes immediately refundable presale contract for testing on the mainnet::

    presale --address=0x8888888888888888888 --days=-1 --minimum=0.001

    Make sure mainnet chain is running, you can connect to it, or you'll get timeout
    Web3 provider is RPC connection http://127.0.0.1:8545
    Deploy address is 0x8888888888888888888
    Deploy address balance is 0.80625992728132232
    Please provide the password to unlock account `0x8888888888888888888`.:
    Deploying presale, tx hash is XXX
    Presale contract address is YYYY
    Presale constructor arguments is 0000000000000000000000000000000000000000000000000000000058d9722800000000000000000000000000000000000000000000000000038d7ea4c68000
    Presale freeze ends at 1490645544
    Presale minimum buy in (wei) is 1000000000000000
    Presale.invest() estimated gas cost is 107700
    Presale.invest() data payload is 0xe8b5e51f
    Presale.refund() data payload is 0x590e1ae3
    All done! Enjoy your decentralized future.
