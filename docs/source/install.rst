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

`Get Solidity compiler <http://solidity.readthedocs.io/en/develop/installing-solidity.html>`_. Use version 0.4.12+. For OSX:

.. code-block:: console

    brew install solidity

Clone this repository from Github using submodules::

    git clone --recursive git@github.com:TokenMarketNet/ico.git

Python 3.5+ required. `See installing Python <https://www.python.org/downloads/>`_.

.. code-block:: console

     python3.5 --version
     Python 3.5.2

Create virtualenv for Python package management in the project root folder (same as where ``setup.py`` is):

.. code-block:: console

    python3.5 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install -e .

Setting up - Ubuntu Linux 16.04
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install dependencies:

.. code-block:: console

    sudo apt install -y git build-essential libssl-dev python3 python3-venv python3-setuptools python3-dev cmake libboost-all-dev

Python 3.5+ required. Make sure you have a compatible version:

.. code-block:: console

     python3.5 --version
     Python 3.5.2

`Install Solidity solc compiler <http://solidity.readthedocs.io/en/develop/installing-solidity.html>`_:

.. code-block:: console

    sudo apt install software-properties-common
    sudo add-apt-repository -y ppa:ethereum/ethereum
    sudo apt update
    sudo apt install -y ethereum solc

Then install ``ico`` Python package and its dependencies:

.. code-block:: console

    git clone # ...
    cd Smart-Contracts
    python3.5 -m venv venv
    source venv/bin/activate
    pip install wheel
    pip install -r requirements.txt
    pip install -e .

Using your desired Solc version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Sometimes it's useful to use some certain version of the Solidity compiler,
this can be done using py-solc package, like this:

.. code-block:: console
    python -m solc.install v0.4.16

If you are lucky, you can now run binary ~/.py-solc/solc-v0.4.16/bin/solc.
The binary is not available every platform.
Remember to update your PATH accordingly:

.. code-block:: console
    export PATH=/home/YOURNAME/.py-solc/solc-v0.4.16/bin:$PATH
