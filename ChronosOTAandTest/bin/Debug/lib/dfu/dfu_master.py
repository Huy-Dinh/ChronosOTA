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
import logging

# Python 3rd party imports
import System

# Nordic libraries
from Nordicsemi import BtUuid, PipeType, PipeStore
from master_emulator import MasterEmulator
from nordicsemi.dfu import dfu_transport_ble
from nordicsemi.dfu.dfu_transport_ble import DfuOpcodesBle

logging = logging.getLogger(__name__)
num_of_send_tries = 1


# Helper functions
def create_byte_array(size, value=0x55):
    """ Create a IronPython byte array with initial value. """
    return System.Array[System.Byte]([value]*size)


class DfuMaster(MasterEmulator):

    def __init__(self, peer_device_address, baud_rate, own_address=None, bond_info=None):
        super(DfuMaster, self).__init__(peer_device_address, baud_rate, own_address, bond_info)
        self.dfu_service_uuid = BtUuid(dfu_transport_ble.UUID_DFU_SERVICE)
        self.dfu_packet_characteristic_uuid = BtUuid(dfu_transport_ble.UUID_DFU_PACKET_CHARACTERISTIC)
        self.dfu_control_characteristic_uuid = BtUuid(dfu_transport_ble.UUID_DFU_CONTROL_STATE_CHARACTERISTIC)
        # self.cccd_descriptor_uuid = dfu_transport_ble.UUID_CLIENT_CHARACTERISTIC_CONFIGURATION_DESCRIPTOR

        self.response_callback = None
        self.notification_callback = None
        self.disconnected_callback = None

        self.pipe_dfu_packet = None
        self.pipe_dfu_control_point = None
        self.pipe_dfu_control_point_notify = None

    def set_notification_callback(self, callback_function):
        self.notification_callback = callback_function

    def set_response_callback(self, callback_function):
        self.response_callback = callback_function

    def set_disconnected_callback(self, callback_function):
        self.disconnected_callback = callback_function

    def setup_service(self):
        """ Set up DFU service database. """
        # Add DFU Service
        self.master.SetupAddService(self.dfu_service_uuid, PipeStore.Remote)

        # Add DFU characteristics
        self.master.SetupAddCharacteristicDefinition(self.dfu_packet_characteristic_uuid, 2, create_byte_array(2))
        self.pipe_dfu_packet = self.master.SetupAssignPipe(PipeType.Transmit)

        self.master.SetupAddCharacteristicDefinition(self.dfu_control_characteristic_uuid, 2, create_byte_array(2))
        self.pipe_dfu_control_point = self.master.SetupAssignPipe(PipeType.TransmitWithAck)
        self.pipe_dfu_control_point_notify = self.master.SetupAssignPipe(PipeType.Receive)

    def open_pipes(self):
        try:
            self.master.OpenRemotePipe(self.pipe_dfu_control_point_notify)
        except Exception:
            logging.error("Failed to open pipes.")
            return False

        return True

    def send_packet_data(self, data):
        self.send_data(self.pipe_dfu_packet,
                       System.Array[System.Byte](data),
                       num_of_send_tries)

    def send_control_data(self, data):
        self.send_data(self.pipe_dfu_control_point,
                       System.Array[System.Byte](data),
                       num_of_send_tries)

    def data_received_handler(self, sender, data_event):
        if data_event.PipeNumber == self.pipe_dfu_control_point_notify:
            op_code = int(data_event.PipeData[0])

            if op_code == DfuOpcodesBle.RESPONSE:
                request_op_code = int(data_event.PipeData[1])
                response_value = int(data_event.PipeData[2])
                self.response_callback(request_op_code, response_value)

            if op_code == DfuOpcodesBle.PKT_RCPT_NOTIF:
                logging.debug("Number of bytes LSB = {0}".format(data_event.PipeData[1]))
                logging.debug("Number of bytes MSB = {0}".format(data_event.PipeData[2]))
                self.notification_callback()

        else:
            logging.debug("Received data on unexpected pipe {0}".format(e.PipeNumber))

    def disconnected_handler(self, sender, e):
        # Set disconnect_event_expected to True to avoid logging "Error: Unexpected disconnection
        # event!" when disconnecting for buttonless DFU.
        self.disconnect_event_expected = True
        super(DfuMaster, self).disconnected_handler(sender, e)
        self.disconnected_callback(e.Value)
