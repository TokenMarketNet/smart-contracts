#!/bin/sh
#
# This is a faux solc stub that runs a dockerized solc
#

VERSION=$SOLC_VERSION

ME=`dirname "$0"`

if [ -z "$SOLC_VERSION" ] ; then
  echo "You need to give SOLC_VERSION environment variable"
  exit 1
fi

# note: I still do not know how to create different path maps for solc. TokenMarket contracts refer to Zeppelin contracts.
# However regardless where you run solc it assumes Zeppelin contracts are within the current working directory
# under zeppelin folder. This is a workaround if you want to invoke populus compile not under this path,
# but some other path and get Populus testrpc fixture working.
# This is mainly a workaround to get our internal test suite to complete. Before this could be maintained
# using a symbolic link, but Docker volume mounts ignore symbolic links.
docker run -i -a stdin -a stdout -a stderr -v `pwd`:`pwd` -v $ME/zeppelin:`pwd`/zeppelin -w `pwd` ethereum/solc:$VERSION "$@" --allow-paths /
