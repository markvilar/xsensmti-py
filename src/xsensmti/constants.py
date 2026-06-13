"""
Xsens USB vendor and product identity constants.
"""

XSENS_USB_VENDOR_ID: int = 0x2639

XSENS_USB_PRODUCT_IDS: dict[int, str] = {
    0x0001: "MTi-10 IMU",
    0x0002: "MTi-20 VRU",
    0x0003: "MTi-30 AHRS",
    0x0011: "MTi-100 IMU",
    0x0012: "MTi-200 VRU",
    0x0013: "MTi-300 AHRS",
    0x0017: "MTi-G 7xx GNSS/INS",
    0x0100: "Body Pack",
    0x0101: "Awinda Station",
    0x0102: "Awinda Dongle",
    0x0103: "Sync Station",
    0x0200: "MTw",
    0x0300: "Motion Tracker Development Board",
    0x0301: "MTi Converter",
    0xD00D: "Wireless Receiver",
}
