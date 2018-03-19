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

    git clone --recursive git@github.com:TokenMarketNet/ico.git
    cd ico
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

If you are lucky, you can now run binary:

.. code-block:: console

    ~/.py-solc/solc-v0.4.16/bin/solc --version

The binary is not available every platform.
Remember to update your PATH accordingly:

.. code-block:: console

    export PATH=$HOME/.py-solc/solc-v0.4.16/bin:$PATH
    # Then you can try if contracts compile correctly
    populus compile

Docker
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TokenMarket contracts can optionally be built, run, and tested using Docker (https://www.docker.com/).
To be able to TokenMarket development environment inside Docker, install Docker and docker-compose (https://docs.docker.com/compose/) first. Then run in ico folder:

.. code-block:: console

    docker-compose up

If everything is ok, you will see something like below:

.. code-block:: console

    MacBook-Pro-mac:docs mac$ docker-compose up

    WARNING: The Docker Engine you're using is running in swarm mode.

    Compose does not use swarm mode to deploy services to multiple nodes in a swarm. All containers will be scheduled on the current node.

    To deploy your application across the swarm, use `docker stack deploy`.

    Starting ganache-cli ... done
    Starting tkn ... done
    Attaching to ganache-cli, tkn
    ganache-cli | Ganache CLI v6.1.0-beta.1 (ganache-core: 2.1.0-beta.1)
    ganache-cli |
    ganache-cli | Available Accounts
    ganache-cli | ==================
    ganache-cli | (0) 0xab2d52942a9875143e94e9fe09a548a45dceb1e8
    ganache-cli | (1) 0xdc4b3cc214b77407ef77f3fa38108a2de48d0cf7
    ganache-cli | (2) 0xaf98b165c2dcadc8e17a717b795ee6dcacf0d306
    ganache-cli | (3) 0xeeb5e1c68201d2fc58e07a2c3619377ea742d0ad
    ganache-cli | (4) 0xa050538c2203055a82bdfc18004c872095283362
    ganache-cli | (5) 0x7b3fe777be5e6b49b3580657ad3792d55e31d0f7
    ganache-cli | (6) 0xc198cf10296d1ed5df408f94890fd57dbad4750c
    ganache-cli | (7) 0xf2dc5b1b4ba8465aac47484ae9dd0ff09844cc27
    ganache-cli | (8) 0xe84316460040659815525165487d436f047fad78
    ganache-cli | (9) 0x1be235ca98cd4a56be34218e8b3265be11bd3f0a
    ganache-cli |
    ganache-cli | Private Keys
    ganache-cli | ==================
    ganache-cli | (0) 29b65e26c903d588f5706d7850cf125f78bef030a993b2a36db859e9f1a4ac3e
    ganache-cli | (1) c7b0146725f16d0e261289e1183304e2f829990bafd695d444b93af995e5c7d7
    ganache-cli | (2) 2dfb4b4e054cc9881ee1170ce5278c65b52e9a5e2afa1f2882376adcd4a339af
    ganache-cli | (3) 00e9470ce3c13cbdbc60e4f2a6c284245ff47a3595d139bef6e04ab3007097e3
    ganache-cli | (4) 613d14fb4045ee80a30649bee4c75d82b7478dab2e834e544e8d4eda8da0915c
    ganache-cli | (5) 8705cfda49b76911fb74ce2b1c704f172070b95e75e4c467e08b99142d531c06
    ganache-cli | (6) 0acaf2b8a74aac3a38406e6a4bc4f6229c2130d1d9e526c7f7a56d5b35e93244
    ganache-cli | (7) b3d28e482d9e1aa3ae696b7f20261200bc077f4771bdb4e202278256b3e94575
    ganache-cli | (8) 3e89a5e223e0919b2b0b61c71590af0f6e96fb0a1c82e0e3ec7a390314b7ded3
    ganache-cli | (9) 6bc7b7209dd5a06cf89876efece6dfd6524f49df039d822d15beaac91afb4d37
    ganache-cli |
    ganache-cli | HD Wallet
    ganache-cli | ==================
    ganache-cli | Mnemonic:      great lunch cushion melt remind harvest taxi prosper hawk ahead split reopen
    ganache-cli | Base HD Path:  m/44'/60'/0'/0/{account_index}
    ganache-cli |
    ganache-cli | Listening on localhost:8545
    ganache-cli | eth_getBalance

To login into dockerized TokenMarket environment:

.. code-block:: console

    docker exec -it tkn /bin/bash

To deploy contract from inside dockerized ico environment (example for Ganache chain address 0xab2d52942a9875143e94e9fe09a548a45dceb1e8):

.. code-block:: console

    python3 ico/cmd/deploycontracts.py --deployment-file crowdsales/crowdsale-token-example-ganache.yml --deployment-name local-token --address 0xab2d52942a9875143e94e9fe09a548a45dceb1e8

The following folders & filles are mapped as volumes so you can edit them from outside Docker and compile/run tests inside Docker:

.. code-block:: console

    contracts
    crowdsales
    zeppelin
    ico
    populus.json
