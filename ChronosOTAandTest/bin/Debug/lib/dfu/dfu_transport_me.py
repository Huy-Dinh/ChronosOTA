# Copyright (c) 2015 Nordic Semiconductor. All Rights Reserved.
#
# The information contained herein is property of Nordic Semiconductor ASA.
# Terms and conditions of usage are described in detail in NORDIC
# SEMICONDUCTOR STANDARD SOFTWARE LICENSE AGREEMENT.
#
# Licensees are granted free, non-transferable use of the information. NO
# WARRANTY of ANY KIND is provided. This heading must NOT be removed from
# the file.

# Python standard library
import time
import struct
import logging

# Nordic libraries
from dfu_master import DfuMaster
from nordicsemi.dfu.dfu_transport import DfuEvent
from nordicsemi.dfu.dfu_transport_ble import DfuTransportBle, DfuOpcodesBle, DfuErrorCodeBle

logging = logging.getLogger(__name__)


class DfuTransportMe(DfuTransportBle):
    def __init__(self, peer_device_address, baud_rate, emulator_id="", own_address=None, bond_info=None):
        super(DfuTransportMe, self).__init__()
        self.dfu_master = DfuMaster(peer_device_address, baud_rate, own_address, bond_info)
        self.emulator_id = emulator_id
        self.dfu_master.set_response_callback(self.response_callback)
        self.dfu_master.set_notification_callback(self.notification_callback)
        self.dfu_master.set_disconnected_callback(self.disconnected_callback)

        self.last_error = DfuErrorCodeBle.SUCCESS
        self.waiting_for_notification = False
        self.last_sent_opcode = DfuOpcodesBle.INVALID_OPCODE
        self.received_response = False

    def get_received_response(self):
        return self.received_response

    def clear_received_response(self):
        self.received_response = False

    def is_waiting_for_notification(self):
        return self.waiting_for_notification

    def set_waiting_for_notification(self):
        self.waiting_for_notification = True

    def get_last_error(self):
        return self.last_error

    def response_callback(self, opcode, error_code):
        logging.debug("Response received for Request Op Code = {0}".format(opcode))

        status_text = DfuErrorCodeBle.error_code_lookup(error_code)

        if opcode == DfuOpcodesBle.START_DFU:
            log_message = "Response for 'Start DFU' received - Status: {0}".format(status_text)
        elif opcode == DfuOpcodesBle.INITIALIZE_DFU:
            log_message = "Response for 'Initialize DFU Params' received - Status: {0}".format(status_text)
        elif opcode == DfuOpcodesBle.RECEIVE_FIRMWARE_IMAGE:
            log_message = "Response for 'Receive FW Data' received - Status: {0}".format(status_text)
        elif opcode == DfuOpcodesBle.VALIDATE_FIRMWARE_IMAGE:
            log_message = "Response for 'Validate' received - Status: {0}".format(status_text)
        else:
            log_message = "Response for Unknown command received."

        logging.debug(log_message)

        if error_code != DfuErrorCodeBle.SUCCESS:
            self._send_event(DfuEvent.ERROR_EVENT, log_message=log_message)
            self.last_error = error_code

        if self.last_sent_opcode == opcode:
            self.received_response = True

    def notification_callback(self):
        if not self.waiting_for_notification:
            log_message = "Packet receipt notification received when it is not expected"
            self._send_event(DfuEvent.ERROR_EVENT, log_message=log_message)
            pass
        else:
            logging.debug("Packet receipt notification received.")
            pass

        self.waiting_for_notification = False

    def disconnected_callback(self, reason):
        logging.debug("Device disconnected, reason: {0}".format(reason))

    def send_packet_data(self, data):
        packet = struct.unpack('B'*len(data), data)
        self.dfu_master.send_packet_data(packet)

    def send_control_data(self, opcode, data=""):
        packet_data = struct.unpack('B'*len(data), data)
        packet = [opcode]
        packet.extend(packet_data)
        self.last_sent_opcode = opcode
        self.dfu_master.send_control_data(packet)

    def open(self):
        log_message = "Connecting..."
        self._send_event(DfuEvent.PROGRESS_EVENT, progress=0, log_message=log_message, done=False)

        if not self.dfu_master.scan_and_connect(emulator_filter=self.emulator_id):
            log_message = "Failed to find or connect to device."
            self._send_event(DfuEvent.PROGRESS_EVENT, progress=0, log_message=log_message, done=True)
            self._send_event(DfuEvent.ERROR_EVENT, log_message=log_message)
            self.last_error = DfuErrorCodeBle.OPERATION_FAILED

        pipes_opened = self.dfu_master.open_pipes()

        if not pipes_opened:
            log_message = "Device does not have the required DFU service"
            self._send_event(DfuEvent.PROGRESS_EVENT, progress=0, log_message=log_message, done=True)
            self._send_event(DfuEvent.ERROR_EVENT, log_message=log_message)
            self.last_error = DfuErrorCodeBle.INVALID_STATE

    def is_open(self):
        return self.dfu_master.connected

    def close(self):
        # wait a second to be able to receive the disconnect event from peer device.
        time.sleep(1)
        # Disconnect from peer device if not done already and clean up.
        self.dfu_master.disconnect()
