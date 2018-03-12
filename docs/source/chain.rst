.. _chain-configuration:

===================
Chain configuration
===================

Introduction
============

*ico* package uses underlying Populus framework to configure different Ethereum backends.

Supported backend and nodes include

* Go Ethereum (geth)

* Parity

* Ethereum mainnet

* Ethereum Ropsten test network

* Ethreum Kovan test network

* ... or basically anything that responds to JSON RPC

Default configuration
=====================

The default configuration set in the packge distribution is in ``populus.json`` file. It is as

* ``http://127.0.0.1:8545`` is mainnet JSON-RPC, `populus.json` network sa `mainnet`

* ``http://127.0.0.1:8546`` is Kovan JSON-RPC, `populus.json` network sa `kovan`

* ``http://127.0.0.1:8547`` is Kovan JSON-RPC, `populus.json` network sa `ropsten`

Ethereum node software (geth, parity) must be started beforehand and configured to allow JSON-RPC in the particular port.

Starting Ethereum node
======================

Go Ethereun mainnet
^^^^^^^^^^^^^^^^^^^

Example how to start Go Ethereum JSON-RPC for mainnet:

.. code-block:: shell

    geth --fast --ipcdisable --rpc --rpcapi "db,eth,net,web3,personal" --verbosity 3 --rpccorsdomain "*"  --cache 2048

You also need to unlock your deployment every time you do a deployment from `geth` console.

Example::

    geth attach http://localhost:8545

Then unlock account for 1 hour:

    personal.unlockAccount("0x00000000...", "your account password", 3600)

Kovan testnet
^^^^^^^^^^^^^

First start `parity --chain=kovan` to generate the chaindata files and such.

Connect to the Parity UI using your web browser.

Create a new Kovan testnet account. The account password will be stored in plain text, so do not use a strong password.

Create a file `password.txt` and store the password there.

Example how to start Parity JSON-RPC for Kovan testnet, unlocking your Kovan account for test transactions. It will permanently unlock your account using the password given in `password.txt` and listen to JSON-RPC in port `http://localhost:8547`.

.. code-block:: shell

    parity --chain=kovan --unlock 0x001fc7d... --password password.txt --jsonrpc-apis "web3,eth,net,parity,traces,rpc,personal" --jsonrpc-port 8547 --no-ipc --port 30306 --tracing on --allow-ips=public

.. note ::

    It is recommended that you use Kovan testnet for any testing and trials, because of faster transaction confirmation times.

Unlocking the deployment account
================================

For Parity you need to have `parity --unlock` given from the command line to unlock the account for automatic access.

For Go Ethereum you need to use `geth console` and run `personal.unlockAccount` to unlock your account for some time, say 3600 seconds, before running scripts.


