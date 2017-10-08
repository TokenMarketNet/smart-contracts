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

Unlocking the deployment account
================================

For Parity you need to have `parity --unlock` given from the command line to unlock the account for automatic access.

For Go Ethereum you need to use `geth console` and run `personal.unlockAccount` to unlock your account for some time, say 3600 seconds, before running scripts.


