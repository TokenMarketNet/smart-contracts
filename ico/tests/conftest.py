"""Test fixtures."""


import pytest
from web3.contract import Contract


def pytest_itemcollected(item):
    """Visualize tests run so we can copy paste output.

    http://stackoverflow.com/q/28898919/315168
    """
    par = item.parent.obj
    node = item.obj
    pref = par.__doc__.strip() if par.__doc__ else par.__class__.__name__
    suf = node.__doc__.strip() if node.__doc__ else node.__name__
    if pref or suf:
        pref = pref.replace(".", ":")
        item._nodeid = ' '.join((pref, suf))
        item._nodeid.rstrip(".")


from ico.tests.fixtures.general import *  # noqa
from ico.tests.fixtures.flatprice import *  # noqa
from ico.tests.fixtures.releasable import *  # noqa
from ico.tests.fixtures.finalize import *  # noqa
