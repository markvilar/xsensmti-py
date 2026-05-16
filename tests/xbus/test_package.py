"""
Unit test for the Xbus package.
"""

import pytest  # noqa: F401


def test_can_import_xsensmti_xbus():
    import xsensmti.xbus as xbus

    assert xbus is not None
    assert hasattr(xbus, "XbusMessage")
