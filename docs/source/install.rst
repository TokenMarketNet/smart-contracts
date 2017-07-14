Installation
============

.. contents:: :local:

Preface
^^^^^^^

Instructions are written in OSX and Linux in mind.

Experience needed

* Basic command line usage

* Basic Github usage

Setting up - OSX
^^^^^^^^^^^^^^^^

Packages needed

* `Populus native dependencies <http://populus.readthedocs.io/en/latest/quickstart.html>`_

Get Solidity compiler. Use version 0.4.8. For OSX:

.. code-block:: console

    brew unlink solidity  # If needed
    # Install 0.4.8
    brew install https://raw.githubusercontent.com/ethereum/homebrew-ethereum/77cce03da9f289e5a3ffe579840d3c5dc0a62717/solidity.rb

Clone this repository from Github.

Python 3.x required. `See installing Python <https://www.python.org/downloads/>`_.

.. code-block:: console

     python3.5 --version
     Python 3.5.2

Create virtualenv for Python package management in the project root folder (same as where ``setup.py`` is):

.. code-block:: console

    python3.5 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Setting up - Ubuntu Linux 16.04
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install dependencies:

.. code-block:: console

    sudo apt install -y git build-essential libssl-dev python3 python3-venv python3-setuptools python3-dev cmake libboost-all-dev

`Install Go Ethereum <https://github.com/ethereum/go-ethereum/wiki/Installation-Instructions-for-Ubuntu>`_:

.. code-block:: console

    sudo apt-get install software-properties-common
    sudo add-apt-repository -y ppa:ethereum/ethereum
    sudo apt-get update
    sudo apt-get install -y ethereum

Currently only Solidity 0.4.8 is supported. Compile it from source. Do this under *a local UNIX user* you are going to solc with, not as root:

.. code-block:: consoile

    git clone --recursive git@github.com:ethereum/solidity.git
    cd solidity
    git checkout 60cc1668517f56ce6ca8225555472e7a27eab8b0
    mkdir build
    cd build
    cmake .. && make
    export PATH=`pwd`/solc:$PATH  # Pu solc to path
    solc --version

Then install ``ico`` Python package and its dependencies:

.. code-block:: console

    git clone # ...
    cd Smart-Contracts
    python3.5 -m venv venv
    source venv/bin/activate
    pip install wheel
    pip install -r requirements.txt
    pip install -e .

Setting up - Ubuntu Linux 14.04
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install dependencies:

.. code-block:: console

    sudo add-apt-repository ppa:fkrull/deadsnakes
    sudo apt-get update
    sudo apt-get install -y python3.5 python3.5-dev
    sudo apt install -y git build-essential python3-setuptools libssl-dev

`Install Go Ethereum <https://github.com/ethereum/go-ethereum/wiki/Installation-Instructions-for-Ubuntu>`_:

.. code-block:: console

    sudo apt-get install software-properties-common
    sudo add-apt-repository -y ppa:ethereum/ethereum
    sudo apt-get update
    sudo apt-get install -y ethereum solc

Then:

.. code-block:: console

    git clone # ...
    cd Smart-Contracts
    python3.5 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python
    pip install -r requirements.txt
    pip install -e .
