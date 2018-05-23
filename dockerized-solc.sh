#!/bin/sh
#
# This is a faux solc stub that runs a dockerized solc
#

VERSION=$SOLC_VERSION

if [ -z "$SOLC_VERSION" ] ; then
  echo "You need to give SOLC_VERSION environment variable"
  exit 1
fi

docker run -i -a stdin -a stdout -a stderr -v `pwd`:`pwd` -w `pwd` ethereum/solc:$VERSION "$@"
