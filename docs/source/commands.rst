.. _command-line:

=====================
Command line commands
=====================

.. contents:: :local:

Introduction
============

``ico`` package provides tooling around deploying and managing token sales and related tasks.

Here are listed some of the available command line commands. For full list see `setup.py <https://github.com/TokenMarketNet/ico/blob/master/setup.py#L61>`_ ``[console-scripts]`` section.

All commands read `populus.json` file for the chain configuration from the current working directory. The chain configuration should set up a Web3 HTTP provider how command line command talks to an Ethereum node. The Ethereum node must have an address with ETH balance for the operations. For more information see :ref:`chain-configuration`.

The most important command is :ref:`deploy-contracts` that allows scripted and orchestrated deployment of multiple related Ethereum smart contracts.


.. _deploy-contracts:

deploy-contracts
================

Scripted deployment of multiple related Ethereum smart contracts.

* Deploy contracts

* Automatically verify contracts on EtherScan

* Link contracts together

* Set common parameters

* Verify contracts have been deployed correctly through assert mechanism

See also :ref:`contract-verification`.

Example YAML deployment scripts

* `allocated-token-sale <https://github.com/TokenMarketNet/ico/blob/master/crowdsales/allocated-token-sale-example.yml>`_ (based on DENT)

* `dummy mintable token sale example <https://github.com/TokenMarketNet/ico/blob/master/crowdsales/example.yml>`_

Help::

    Usage: deploy-contracts [OPTIONS]

      Makes a scripted multiple contracts deployed based on a YAML file.

      Reads the chain configuration information from populus.json. The resulting
      deployed contracts can be automatically verified on etherscan.io.

      Example:

          deploy-contracts --deployment-file=crowdsales/example.yml
          --deployment-name=kovan--
          address=0x001fc7d7e506866aeab82c11da515e9dd6d02c25

      Example files:

      * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/allocated-
      token-sale-example.yml

      * https://github.com/TokenMarketNet/ico/blob/master/crowdsales/example.yml

    Options:
      --deployment-name TEXT  YAML section name we are deploying. Usual options
                              include "mainnet" or "kovan"  [required]
      --deployment-file TEXT  YAML file definiting the crowdsale  [required]
      --address TEXT          Deployment address that pays the gas for the
                              deployment cost. This account must exist on Ethereum
                              node you are connected to.  [required]
      --help                  Show this message and exit.


deploy-token
============

Deploy a single token contract.

Example usage::

    deploy-token --help
    Usage: deploy-token [OPTIONS]

      Deploy a single crowdsale token contract.

      Examples:

      deploy-token --chain=ropsten
      --address=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6 --name="MikkoToken
      2.0" --symbol=MOO --release-
      agent=0x3c2d4e5eae8c4a31ccc56075b5fd81307b1627c6  --supply=100000

      deploy-token --chain=kovan --contract-name="CentrallyIssuedToken"
      --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25  --name="TestToken"
      --symbol=MOO --supply=916 --decimals=0 --verify --verify-
      filename=CentrallyIssuedToken.sol

    Options:
      --chain TEXT            On which chain to deploy - see populus.json
      --address TEXT          Address to deploy from and who becomes as a owner
                              (must exist on geth)  [required]
      --contract-name TEXT    Name of the token contract
      --release-agent TEXT    Address that acts as a release agent (can be same as
                              owner)
      --minting-agent TEXT    Address that acts as a minting agent (can be same as
                              owner)
      --name TEXT             Token name  [required]
      --symbol TEXT           Token symbol  [required]
      --supply INTEGER        Initial token supply (multipled with decimals)
      --decimals INTEGER      How many decimal points the token has
      --verify / --no-verify  Verify contract on EtherScan.io
      --verify-filename TEXT  Solidity source file of the token contract for
                              verification
      --master-address TEXT   Move tokens and upgrade master to this account
      --help                  Show this message and exit.

distribute-tokens
=================

Help::

    Usage: distribute-tokens [OPTIONS]

      Distribute tokens to centrally issued crowdsale participant or bounty
      program participants.

      Reads in distribution data as CSV. Then uses Issuer contract to distribute
      tokens. All token counts are multiplied by token contract decimal
      specifier. E.g. if CSV has amount 15.5, token has 2 decimal places, we
      will issue out 1550 raw token amount.

      To speed up the issuance, transactions are verified in batches. Each batch
      is 16 transactions at a time.

      Example (first run):

          distribute-tokens --chain=kovan
          --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25
          --token=0x1644a421ae0a0869bac127fa4cce8513bd666705 --master-
          address=0x9a60ad6de185c4ea95058601beaf16f63742782a --csv-
          file=input.csv --allow-zero --address-column="Ethereum address"
          --amount-column="Token amount"

      Example (second run, continue after first run was interrupted):

          distribute-tokens --chain=kovan
          --address=0x001FC7d7E506866aEAB82C11dA515E9DD6D02c25
          --token=0x1644a421ae0a0869bac127fa4cce8513bd666705 --csv-
          file=input.csv --allow-zero --address-column="Ethereum address"
          --amount-column="Token amount" --issuer-
          address=0x2c9877534f62c8b40aebcd08ec9f54d20cb0a945

    Options:
      --chain TEXT                    On which chain to deploy - see populus.json
      --address TEXT                  The account that deploys the issuer
                                      contract, controls the contract and pays for
                                      the gas fees  [required]
      --token TEXT                    Token contract address  [required]
      --csv-file TEXT                 CSV file containing distribution data
                                      [required]
      --address-column TEXT           Name of CSV column containing Ethereum
                                      addresses
      --amount-column TEXT            Name of CSV column containing decimal token
                                      amounts
      --limit INTEGER                 How many items to import in this batch
      --start-from INTEGER            First row to import (zero based)
      --issuer-address TEXT           The address of the issuer contract - leave
                                      out for the first run to deploy a new issuer
                                      contract
      --master-address TEXT           The team multisig wallet address that does
                                      StandardToken.approve() for the issuer
                                      contract
      --allow-zero / --no-allow-zero  Stops the script if a zero amount row is
                                      encountered
      --help                          Show this message and exit.

token-vault
===========

Help::

    token-vault --help
    Usage: token-vault [OPTIONS]

      TokenVault control script.

      1) Deploys a token vault contract

      2) Reads in distribution data as CSV

      3) Locks vault

    Options:
      --action TEXT                   One of: deploy, load, lock
      --chain TEXT                    On which chain to deploy - see populus.json
      --address TEXT                  The account that deploys the vault contract,
                                      controls the contract and pays for the gas
                                      fees  [required]
      --token-address TEXT            Token contract address  [required]
      --csv-file TEXT                 CSV file containing distribution data
      --address-column TEXT           Name of CSV column containing Ethereum
                                      addresses
      --amount-column TEXT            Name of CSV column containing decimal token
                                      amounts
      --limit INTEGER                 How many items to import in this batch
      --start-from INTEGER            First row to import (zero based)
      --vault-address TEXT            The address of the vault contract - leave
                                      out for the first run to deploy a new issuer
                                      contract
      --freeze-ends-at INTEGER        UNIX timestamp when vault freeze ends for
                                      deployment
      --tokens-to-be-allocated INTEGER
                                      Manually verified count of tokens to be set
                                      in the vault
      --help                          Show this message and exit.

combine-csvs
============

Help::

    combine-csvs --help
    Usage: combine-csvs [OPTIONS]

      Combine multiple token distribution CSV files to a single CSV file good
      for an Issuer contract.

      - Input is a CSV file having columns Ethereum address, number of tokens

      - Round all tokens to the same decimal precision

      - Combine multiple transactions to a single address to one transaction

      Example of cleaning up one file:

          combine-csvs --input-file=csvs/bounties-unclean.csv --output-
          file=combine.csv --decimals=8 --address-column="address" --amount-
          column="amount"

      Another example - combine all CSV files in a folder using zsh shell:

          combine-csvs csvs/*.csv(P:--input-file:) --output-file=combined.csv
          --decimals=8 --address-column="Ethereum address" --amount-
          column="Total reward"

    Options:
      --input-file TEXT      CSV file to read and combine. It should be given
                             multiple times for different files.  [required]
      --output-file TEXT     A CSV file to write the output  [required]
      --decimals INTEGER     A number of decimal points to use  [required]
      --address-column TEXT  Name of CSV column containing Ethereum addresses
      --amount-column TEXT   Name of CSV column containing decimal token amounts
      --help                 Show this message and exit.


