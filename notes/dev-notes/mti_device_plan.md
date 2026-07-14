For the MtiDevice, I think we should only support a subset of the features of the XsDevice for now.

1. Identity functionality - device_id(), product_code(), firmware_version(), hardware_version(), port_name(), port_info(), baud_rate()
2. State functionality - goto_config(), goto_measurement(), device_state(), is_measuring(), reset(), reset_factory_default()
3. Output configuration - set_output_config, output_config
4. Data retrieval - take_first_data_packet_in_queue(), last_available_live_data(), request_data
5. Raw comms. - send_custom_message(), send_raw_message(), reopen_port()

