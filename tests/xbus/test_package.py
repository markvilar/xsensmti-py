"""
Unit test for the Xbus package.
"""

import pytest  # noqa: F401


def test_can_import_xsens_xbus():
    import xsens.xbus as xbus

    assert xbus is not None
    assert hasattr(xbus, "XbusMessage")
