=====
Other
=====

.. contents:: :local:

Importing raw keys
==================

You often need need to work with raw private keys. To import a raw private key to geth you can do from console::

    web3.personal.importRawKey("<Private Key>","<New Password>")

Private key must be **without** 0x prefixed hex format.

More information

* http://ethereum.stackexchange.com/a/10020/620
