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

Flattening source code for verification
=======================================

Here is a snippet that will expand the source code of all contracts for the generated ``build/contracts.json`` file and embed the source inside the file. This will allow easier verification (reproducible builds) when using ABI data.

You can run from Python shell:

.. code-block:: python

    import populus
    import json
    from ico.importexpand import expand_contract_imports

    p = populus.Project()
    data = json.load(open("build/contracts.json", "rt"))
    for contract in data.values():

        # This was a source code file for an abstract contract
        if not contract["metadata"]:
            continue

        targets = contract["metadata"]["settings"]["compilationTarget"]

        contract_file = list(targets.keys())[0]  # "contracts/AMLToken.sol": "AMLToken"

        # Eliminate base path, as this will be set by expand_contract_imports
        if "zeppelin/" not in contract_file:
            contract_file = contract_file.replace("contracts/", "")
        else:
            pass
            # contract_file = contract_file.replace("zeppelin/", "zeppelin/contracts/")

        source, imports = expand_contract_imports(p, contract_file)
        contract["source"] = source

    # Write out expanded ABI data
    json.dump(data, open("build/contracts-flattened.json", "wt"))
