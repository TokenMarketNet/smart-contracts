=================================
Contract source code verification
=================================

.. contents:: :local:

Verifying contracts on EtherScan
================================

ICO package has a semi-automated process to verify deployed contracts on `EtherScan verification service <https://etherscan.io/verifyContract>`_.

Benefits of verification
========================

* You can see the state of your contract variables real time on EtherScan block explorer

* You prove that there are deterministic and verifiable builds for your deployed smart contracts

How verification works
======================

* You need to have Firefox installed with necessary Selenium drivers

* Give `--verify` option to a :ref:`deployment script <command-line>`

* After the command line script has deployed the contract a browser will open

* The script autofills the verification page details (source code, construction arguments, linked libraries)

.. image:: screenshots/etherscan_verify.png
    :width: 600
