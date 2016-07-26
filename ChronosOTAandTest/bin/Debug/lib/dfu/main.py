import time
import argparse
import sys
import os
import clr
sys.path.append(r'.\..')

try:
    programfilesPath = os.environ['PROGRAMFILES']
    masterApiBasePath = os.path.join(programfilesPath, r'Nordic Semiconductor\Master Emulator')
    dirsandfiles = os.listdir(masterApiBasePath)
    dirs = []
    for element in dirsandfiles:
        if os.path.isdir(os.path.join(masterApiBasePath, element)):
            dirs.append(element)
    if len(dirs) == 0:
        raise Exception('Master Emulator directory not found.')
    dirs.sort()
    masterApiPath = os.path.join(masterApiBasePath, dirs[-1])
    print masterApiPath
    sys.path.append(masterApiPath)
    clr.AddReferenceToFile("MasterEmulator.dll")
except Exception, e:
    raise Exception("Cannot load MasterEmulator.dll")

from nordicsemi.dfu.dfu import Dfu
from dfu_transport_me import DfuTransportMe

def main():
    parser = argparse.ArgumentParser(description='Send hex file over-the-air via BLE')
    parser.add_argument('--file', '-f',
                        type=str,
                        required=True,
                        dest='file',
                        help='Filename of Hex file.')
    parser.add_argument('--address', '-a',
                        type=str,
                        required=True,
                        dest='address',
                        help='Advertising address of nrf51822 device.')
    parser.add_argument('--baud-rate', '-b',
                        type=int,
                        required=False,
                        dest='baud_rate',
                        default=1000000,
                        help='Baud rate for communication with the master emulator device. Default 1000000.')
    parser.add_argument('--emulator-id', '-e',
                        type=str,
                        required=False,
                        dest='emulator_id',
                        default='',
                        help='COM port the master emulator device is connected to, e.g. COM1')

    args = parser.parse_args()
    print 'Sending file {0} to device {1}'.format(args.file, args.address.upper())
    print 'Using baud rate {0}'.format(args.baud_rate)


    # TODO: Fill DfuTransportMe() constructor with init parameters
    # args.address needed
    # args.baud_rate needed
    dfu_backend = DfuTransportMe(args.address.upper(), args.baud_rate, args.emulator_id)

    dfu = Dfu(args.file, dfu_backend)

    # Transmit the hex image to peer device.
    dfu.dfu_send_images()

if __name__ == '__main__':
    main()
