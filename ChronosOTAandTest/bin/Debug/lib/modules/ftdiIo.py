# @file
#
import sys
import ftd2xx
from array import array
import time

class FtdiButtonIo(object):
    def __init__(self, ftdi, ioline, sampleSpeed = 0.50):
        self.ftdi = SimpleSPI()
        self.default = (0x20 | ioline)
        self.ioline = ioline
        self.ftdi.open(ftdi, (self.default | 0x40 ), self.default, False)
        self.sampleSpeed = sampleSpeed
    
    def buttonPress(self):
        self.ftdi.gpioWrite(self.default&~self.ioline)
    
    def buttonRelease(self):
        self.ftdi.gpioWrite(self.default)
    
    def buttonDuration(self, duration):
        self.buttonPress()
        time.sleep(duration)
        self.buttonRelease()
        time.sleep(self.sampleSpeed)
    
    def gpioRead(self):
        return self.ftdi.gpioRead()
    
    def reset(self):
        self.ftdi.gpioWrite(self.ioline)
        time.sleep(0.1)
        self.ftdi.gpioWrite(self.default)
        

class SimpleSPI(object):

    STATUS_OK                   = 0x00
    STATUS_ERROR                = 0x01
    STATUS_UNKNOWN_DEVICE       = 0x02
    SPI_MODE_MSB_FIRST          = False
    gpio_read_array = array('B',(0x81,))
    
    def __init__(self):
        self.ftdi = None
        self.MASK = 0xFF
        self.GPIO = 0x00
        # ftd2xx.rescan()            

    def open(self, serial, ioDir, default_io_state, SPI_MODE_MSB):
        
        self.serial = serial
        self.MASK = ioDir
        self.GPIO = default_io_state

        if serial != '':                            # If serial number is specified
            d =serial +'A'                          # Generate valid device serial number
            self.ftdi = ftd2xx.openEx(d)
        else:
            self.ftdi = ftd2xx.open(0)

        if SPI_MODE_MSB == True:
            SPI_MODE_MSB_FIRST = True
        else:
            SPI_MODE_MSB_FIRST = False

        self.ftdi.setBitMode(self.MASK, 0x02)           # MPSSE mode 
        self.ftdi.setTimeouts(1000, 1000)
        self.ftdi.setLatencyTimer(1)
        configBuf = array('B')
        configBuf.extend([0x86, 0x16, 0x00])            #  Clock divisor: 0x0004  Formula: TCK/SK period = 12MHz / ((1+[(0xValueH*256) OR 0xValueL])*2)
        configBuf.extend([0x85])                        # Disable loop-back
        self.ftdi.write(configBuf.tostring())
        self.ftdi.purge()                               # Purge receive and transmit buffer
        return self.STATUS_OK
    
    def _open(self):
        self.open(self.serial, self.MASK, self.GPIO, True)
        
    # @brief Close device
    def close(self):
        try:
            self.ftdi.close()
            return self.STATUS_OK
        except:
            return self.STATUS_ERROR
    
    def reset(self):
        try:
            return self.ftdi.resetDevice()
        except:
            return self.STATUS_ERROR
            

    def updateGPIO(self):
        buf = array('B')
        buf.extend((0x80, self.GPIO, self.MASK))
        self.ftdi.write(buf.tostring())

    def gpioWrite(self, io):
        self.GPIO = io
        # self.GPIO &= 0x07        # Clear old values in shadow register.
        # self.GPIO |=(io)    # Set new values in shadow register, retain SPI values.
        # self.GPIO |=(io&0xF8)    # Set new values in shadow register, retain SPI values.
        self.updateGPIO()
        
    def gpioRead(self):
        self.ftdi.write(self.gpio_read_array.tostring())
        while self.ftdi.getStatus()[0] < 1:
            pass
      
        ret = self.ftdi.read(1)
        c = array('B')
        c.fromstring(ret)
        return c[0]
      
    def spiWrite(self,payload):
        mbuf = array('B')
        mbuf.extend(payload)
        self.ftdi.write(mbuf.tostring())
        
    def spiWrite2(self, payload):
        mbuf = array('B')
        mbuf.extend((0x80, self.GPIO&~(0x08), self.MASK))
        if self.SPI_MODE_MSB_FIRST:
            # SPI: Clock Data Bytes In on +ve Clock Edge MSB First (no Write)
            mbuf.extend((0x11, len(payload)-1, 0))
        else:
            # SPI: Clock Data Bytes In on +ve Clock Edge LSB First (no Write)
            mbuf.extend((0x19, len(payload)-1, 0))
        mbuf.extend(payload)
        mbuf.extend((0x80, self.GPIO, self.MASK))

        self.ftdi.write(mbuf.tostring())
        # Just read and throw away the data acquired
        # ret = self.ftdi.read(len(packet))
        
        
    def spiRead2(self, length):
        if length > 0:
            pass
        else:
            return self.STATUS_ERROR
      
        mbuf = array('B')
        mbuf.extend((0x80, self.GPIO&~(0x08), self.MASK))
        if self.SPI_MODE_MSB_FIRST:
            # SPI: Clock Data Bytes In on +ve Clock Edge MSB First (no Write)
            mbuf.extend((0x20, length-1, 0))
        else:
            # SPI: Clock Data Bytes In on +ve Clock Edge LSB First (no Write)
            mbuf.extend((0x28, length-1, 0))
        mbuf.extend((0x80, self.GPIO, self.MASK))
        self.ftdi.write(mbuf.tostring())
        
        while self.ftdi.getStatus()[0] < length:
            pass
        ret = self.ftdi.read(length)
        c = array('B')
        c.fromstring(ret)
        return c

    def spiReadWrite2(self, length, payload):
        if length > 0:
            pass
        else:
            return self.STATUS_ERROR

        mbuf = array('B')
        mbuf.extend((0x80, self.GPIO&~(0x08), self.MASK))   # CSN = 0
        if self.SPI_MODE_MSB_FIRST:
            # SPI: Out on negative edge, in on positive edge (MSB first)
            mbuf.extend((0x31, length-1, 0))
        else:
            # SPI Out on negative edge, in on positive edge (LSB first)
            mbuf.extend((0x39, length-1, 0))
        mbuf.extend(payload)
        mbuf.extend((0x80, self.GPIO, self.MASK))

        self.ftdi.write(mbuf.tostring())
        
        time.sleep(0.0001)
        tmp = self.ftdi.getStatus()[0]
        while tmp != self.ftdi.getStatus()[0]:
            tmp = self.ftdi.getStatus()[0]
        
        ret = self.ftdi.read(self.ftdi.getStatus()[0])
        c = array('B')
        c.fromstring(ret)
        return [int(el) for el in c.tolist()]

    def listDevices(self):
        return ftd2xx.listDevices()
