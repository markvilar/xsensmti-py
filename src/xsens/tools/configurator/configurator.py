"""
Configurator for XSens MTi devices.
"""

from __future__ import annotations

import serial

from loguru import logger
from xsens.xbus.datatypes import XbusMessage, XbusMessageID
from ..serial_io import open_serial_port, send_and_receive
from .presets import OutputPreset, build_output_configuration_payload


def configure_device(
    port: str,
    baud: int = 115200,
    preset: OutputPreset = (),
    timeout: float = 5.0,
) -> None:
    """
    Configure an MTi device at port with the given output preset.

    Transitions the device to config mode, applies the output configuration,
    then returns it to measurement mode. Raises domain exceptions on failure;
    caller is responsible for handling them.
    """
    ser: serial.Serial | None = None

    try:
        ser = open_serial_port(port, baud, read_timeout=0.1)
        ser.reset_input_buffer()

        logger.info(f"Entering configuration mode on {port}...")
        send_and_receive(
            ser,
            XbusMessageID.GOTOCONFIG,
            expected_mid=XbusMessageID.GOTOCONFIG_ACK,
            timeout=timeout,
        )

        device_id_msg: XbusMessage = send_and_receive(
            ser,
            XbusMessageID.REQ_DEVICE_ID,
            expected_mid=XbusMessageID.DEVICE_ID,
            timeout=timeout,
        )
        device_id: int = int.from_bytes(device_id_msg.payload, "big")
        logger.info(f"Device ID: {device_id:#010x}")

        payload: bytes = build_output_configuration_payload(preset)
        logger.info(f"Applying output configuration ({len(preset)} outputs)...")
        send_and_receive(
            ser,
            XbusMessageID.OUTPUT_CONFIGURATION,
            payload=payload,
            expected_mid=XbusMessageID.OUTPUT_CONFIGURATION_ACK,
            timeout=timeout,
        )

        logger.info("Entering measurement mode...")
        send_and_receive(
            ser,
            XbusMessageID.GOTOMEASUREMENT,
            expected_mid=XbusMessageID.GOTOMEASUREMENT_ACK,
            timeout=timeout,
        )

    finally:
        if ser is not None:
            ser.close()
