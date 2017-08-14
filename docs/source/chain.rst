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

* ``http://127.0.0.1:8545`` is mainnet JSON-RPC

* ``http://127.0.0.1:8546`` is Kovan JSON-RPC
