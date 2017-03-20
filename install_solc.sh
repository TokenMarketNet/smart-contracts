#!/bin/bash
#
# Install solc 
#

set -e
set -u

mkdir -p solc-versions/solc-$SOLC_VERSION
cd solc-versions/solc-$SOLC_VERSION
git clone --recurse-submodules --branch v$SOLC_VERSION --depth 50 https://github.com/ethereum/solidity.git
./solidity/scripts/install_deps.sh
wget https://github.com/ethereum/solidity/releases/download/v$SOLC_VERSION/solidity-ubuntu-trusty.zip
unzip solidity-ubuntu-trusty.zip
echo "Solidity installed at $TRAVIS_BUILD_DIR/solc-versions/solc-$SOLC_VERSION/solc"
tree $TRAVIS_BUILD_DIR/solc-versions/solc-$SOLC_VERSION
