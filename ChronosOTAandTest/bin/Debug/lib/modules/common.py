#! /usr/bin/python
from array import array
import os

class Utilities:
    
    @staticmethod
    def littleEndian(value, byte = None):
        from math import ceil,log
        
        temp = []
        if byte == None:
            if value != 0:
                size = ceil(log(float(value),256))
            else:
                size = 2
            
            if size > 2:
                byte = 16
            else:
                byte = 2
        for i in range(byte):
            temp.append(int("%02X" % ((value >> i*8) & 0xFF),16))
        
        del ceil,log
        
        return temp
    
    @staticmethod
    def getAddressFromInfopageFile(infopageFile):
        if not os.path.exists(infopageFile):
            return False
        else:
            file = open(infopageFile,'r')
            Address = []
            for i in range(6):
                x = file.read(2)
                #Address.append(int(x,16))
                Address.append(x)
                file.read(1)
            staticAddr = int(Address[-1],16) | 0xC0
            # Address[-1] = str(hex(staticAddr)).lstrip('0x')
            Address[-1] = str.upper(str(hex(staticAddr)).lstrip('0x'))
            dutAddress = "".join(["%s" % x for x in Address[::]])
            return dutAddress
        
class Uuid:
    assignedNumbers = {
          'GAP'                     :0x1800
        , 'DEVICE_NAME'             :0x2A00
        , 'APPEARANCE'              :0x2A01
        , 'PRIVACY_FLAG'            :0x2A02
        , 'RECONN_ADDR'             :0x2A03
        , 'CONNECTION_PARAMETERS'   :0x2A04
        , 'GATT'                    :0x1801
        , 'SERVICE_CHANGED'         :0x2A05
        , 'PRIMARY_SERVICE'         :0x2800
        , 'SECONDARY_SERVICE'       :0x2801
        , 'INCLUDE'                 :0x2802
        , 'CHARACTERISTIC'          :0x2803
        , 'CHARACTERISTIC_EXT_PROP' :0x2900
        , 'CHARACTERISTIC_USER_DESC':0x2901
        , 'CHARACTERISTIC_CLT_CFG'  :0x2902
        , 'CHARACTERISTIC_SVR_CFG'  :0x2903
        , 'CHARACTERISTIC_FORMAT'   :0x2904
        , 'CHARACTERISTIC_AGG_FMT'  :0x2905
    }
    groupingUuids = [
        assignedNumbers['PRIMARY_SERVICE'],
        assignedNumbers['SECONDARY_SERVICE'],
    ]
    
class ByteArray(array):
    mode = 'MSB'
    def __rshift__(self, other):
        tmp = 0
        if self.mode == 'MSB':
            tmparray = self[::]
        elif self.mode == 'LSB':
            tmparray = self[-1::-1]
        for el in tmparray:
            tmp = (tmp << 8) | el
        tmp = tmp >> other
        tmpArray = ByteArray('B')
        for i in range(len(self)):
            if self.mode == 'MSB':
                tmpArray.extend([(tmp >> (120-(8*i))) & 0xFF])
            elif self.mode == 'LSB':
                tmpArray.extend([(tmp >> (8*i)) & 0xFF])
        return tmpArray
            
    def __lshift__(self, other):
        tmp = 0
        if self.mode == 'MSB':
            tmparray = self[::]
        elif self.mode == 'LSB':
            tmparray = self[-1::-1]
        for el in tmparray:
            tmp = (tmp << 8) | el
        tmp = tmp << other
        tmpArray = ByteArray('B')
        for i in range(len(self[::])):
            if self.mode == 'MSB':
                tmpArray.extend([(tmp >> (120-(8*i))) & 0xFF])
            elif self.mode == 'LSB':
                tmpArray.extend([(tmp >> (8*i)) & 0xFF])
        return tmpArray
    
    def __xor__(self, other):
        tmpArray = ByteArray('B')
        for i in range(len(self)):
            tmpArray.extend([self[i] ^ other[i]])
        return tmpArray
        
class DefaultPktFunctions(object):
    def __getattr__(self, name):
        print "Call to unknown attribute %s" % name
        return None
    
    def __getitem__(self,key):
        return self.Content[key]
        
    def __contains__(self,item):
        return item in self.__dict__
    
    def __eq__(self, other):
        return self.Content == other
        
    def __ne__(self, other):
        return self.Content <> other
    
    def __iter__(self):
        return iter(self.Content)
    
    def __str__(self):
        return '['+', '.join('0x%02X' % el for el in self.Content) + ']'
    
    def __repr__(self):
        return "%s" % (self.__class__)

    def __add__(self, other):
        self.Content = self.Content + other
        return self.Content
        
    def __radd__(self, other):
        return other + self.Content

        
    def __iadd__(self, other):
        self.Content = self.Content + other
        return self.Content
        
    def __len__(self):
        return len(self.Content)


class PacketLengthError(Exception):
    def __init__(self, pktType, packet):
        self.pktType = pktType
        self.packet = packet
    
    def __str__(self):
        return "Packet Length error occured while generating %r from [%s]" % (self.pktType,", ".join("0x%02X" % el for el in self.packet))