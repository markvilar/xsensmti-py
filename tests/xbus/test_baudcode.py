"""
Tests for XbusBaudCode, the wire encoding of a baud rate.
"""

import pytest

from xsensmti.xbus import XbusBaudCode


@pytest.mark.parametrize(
    ("code", "rate"),
    [
        (XbusBaudCode.BAUD_460800, 460800),
        (XbusBaudCode.BAUD_230400, 230400),
        (XbusBaudCode.BAUD_115200, 115200),
        (XbusBaudCode.BAUD_76800, 76800),
        (XbusBaudCode.BAUD_57600, 57600),
        (XbusBaudCode.BAUD_38400, 38400),
        (XbusBaudCode.BAUD_28800, 28800),
        (XbusBaudCode.BAUD_19200, 19200),
        (XbusBaudCode.BAUD_14400, 14400),
        (XbusBaudCode.BAUD_9600, 9600),
        (XbusBaudCode.BAUD_921600, 921600),
        (XbusBaudCode.BAUD_4800, 4800),
        (XbusBaudCode.BAUD_2000000, 2000000),
        (XbusBaudCode.BAUD_4000000, 4000000),
        (XbusBaudCode.BAUD_3500000, 3500000),
        (XbusBaudCode.BAUD_921600_LEGACY, 921600),
    ],
)
def test_code_maps_to_rate(code: XbusBaudCode, rate: int) -> None:
    assert code.to_rate() == rate


def test_to_rate_is_total() -> None:
    """Every code must map to a rate — a missing entry would raise KeyError."""
    for code in XbusBaudCode:
        assert code.to_rate() > 0


def test_default_baud_rate_is_the_documented_code() -> None:
    assert XbusBaudCode.BAUD_115200 == 0x02
    assert XbusBaudCode(0x02).to_rate() == 115200


def test_both_921600_codes_encode_the_same_rate() -> None:
    assert XbusBaudCode.BAUD_921600 != XbusBaudCode.BAUD_921600_LEGACY
    assert (
        XbusBaudCode.BAUD_921600.to_rate()
        == XbusBaudCode.BAUD_921600_LEGACY.to_rate()
        == 921600
    )


def test_mapping_is_not_ordered() -> None:
    """0x0A is 921600 while the adjacent 0x0B is 4800 — a lookup, not arithmetic."""
    assert XbusBaudCode(0x0A).to_rate() == 921600
    assert XbusBaudCode(0x0B).to_rate() == 4800
