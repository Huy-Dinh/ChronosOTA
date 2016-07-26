#! /usr/bin/python
from modules.common import DefaultPktFunctions, Utilities
# import Exceptions
from modules.common import PacketLengthError

class AttPkt(DefaultPktFunctions):
    def __new__(clr, *args, **argv):
        if ('packet' in argv and clr == AttPkt):
            # Check if the Code is in the valid codes
            opcode = argv['packet'][0]
            if opcode in opcodeLookup:
                # Fetching the packet type to generate
                packetType = opcodeLookup[opcode]['Pkt']
                # Checking if the packet size is within the valid bounds
                if not opcodeLookup[opcode]['minSize'] <= len(argv['packet']) <= opcodeLookup[opcode]['maxSize']:
                    # if the packet is outside the valid bounds, return an PacketLengthError
                    raise PacketLengthError(packetType,argv['packet'])

                # Generate and return the correct packet type
                return super(AttPkt, packetType).__new__(packetType)
            # Checking if we need to construct a AttCommand packet if it is unknown
            elif opcode & 0x40:
                return super(AttPkt, AttCommand).__new__(AttCommand)
            # If the opcode were not in the "known" packet list, return a General ATT Packet
            return super(AttPkt, GeneralAttPacket).__new__(GeneralAttPacket)
        # The packet type to construct is know, noo need to find the Packet Type to construct
        return super(AttPkt,clr).__new__(clr)

    def __init__(self, *args, **argv):
        self.Content = []
        # If 'packet' is in the argv, we know it has to be parsed (all classes need to implement create, build and parse)
        if 'packet' in argv:
            packet = argv['packet']
            # Putting the packet inside the Content of the Class
            self.Content = [int(el) for el in packet]
            # Defining the opcode of the Class
            self.Opcode = packet[0]
            # Parsing the packet
            self.parse(packet)
        else:
            # It was a known packet, let's fetch the Opcode for it
            self.Opcode = [None,pktLookup[self.__class__]['Opcode']][self.__class__ in pktLookup]
            # Send all the arguments to the Class, and let it populate it
            self.create(*args,**argv)
            # Build the Content of the class.
            self.build()

    def parse(self, packet):
        pass
    def create(self, *args, **argv):
        pass
    def build(self):
        pass

class AttCommand(AttPkt):
    EventCode = 0x95 # SerialCommTypeMapping.ATT_COMMAND_EVENTCODE

class AttRequest(AttPkt):
    EventCode = 0x95 # SerialCommTypeMapping.ATT_COMMAND_EVENTCODE

class AttResponse(AttPkt):
    EventCode = 0x96 # SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE

class AttNotification(AttPkt):
    EventCode = 0x94 # SerialCommTypeMapping.ATT_NOTIFY_EVENTCODE

class AttIndication(AttPkt):
    EventCode = 0x94 # SerialCommTypeMapping.ATT_NOTIFY_EVENTCODE

class AttConfirmation(AttPkt):
    EventCode = 0x96 # SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE

class GeneralAttPacket(AttPkt):
    EventCode = 0x96 # SerialCommTypeMapping.ATT_RESPONSE_EVENTCODE
    def parse(self, packet):
        pass
        # todo decode Authenticated flag and signature

class Attribute:
    def __init__(self, handle, uuid, value=None, endHandle=None):
        self.handle = handle
        self.endHandle = endHandle
        self.uuid = uuid
        self.value = []
        if value != None:
            for v in value:
                self.value.append(int(v))

class AttributeFound:
    def __init__(self, foundHandle, endFoundHandle, value = None):
        self.foundHandle = foundHandle
        self.endFoundHandle = endFoundHandle
        self.value = value

class AttErrorResponse(AttResponse):
    def create(self, ErrorOpcode = 0x00, Handle = 0x00, ErrorCode=0x01):
        self.ErrorOpcode = ErrorOpcode & 0xFF
        self.Handle = Handle & 0xFFFF
        self.ErrorCode = ErrorCode & 0xFF

    def build(self):
        self.Content = [self.Opcode, self.ErrorOpcode,
            self.Handle & 0xFF, (self.Handle >> 8) & 0xFF,
            self.ErrorCode]

    def parse(self, packet):
        self.ErrorOpcode = self.Content[1]
        self.Handle = (self.Content[3] << 8) | self.Content[2]
        self.ErrorCode = self.Content[4]

class AttExchangeMtuRequest(AttRequest):
    def create(self, RxMtu = 23):
        self.RxMtu = RxMtu & 0xFFFF

    def build(self):
        self.Content = [self.Opcode, self.RxMtu & 0xFF, (self.RxMtu >> 8) & 0xFF]

    def parse(self, packet):
        self.RxMtu = (self.Content[2] << 8) | self.Content[1]

class AttExchangeMtuResponse(AttResponse):
    def create(self, RxMtu = 23):
        self.RxMtu = RxMtu & 0xFFFF

    def build(self):
        self.Content = [self.Opcode, self.RxMtu & 0xFF, (self.RxMtu >> 8) & 0xFF]

    def parse(self, packet):
        self.RxMtu = (self.Content[2] << 8) | self.Content[1]

class AttFindInformationRequest(AttRequest):
    def create(self, StartHdl=0x0001, EndHdl=0xFFFF):
        self.StartHdl = StartHdl & 0xFFFF
        self.EndHdl = EndHdl & 0xFFFF

    def build(self):
        self.Content = [self.Opcode,
            self.StartHdl & 0xFF, (self.StartHdl >> 8) & 0xFF,
            self.EndHdl & 0xFF, (self.EndHdl >> 8) & 0xFF]

    def parse(self, packet):
        self.StartHdl = self.Content[1] | (self.Content[2] << 8)
        self.EndHdl = self.Content[3] | (self.Content[4] << 8)

class AttFindInformationResponse(AttResponse):
    def create(self, Attributes = [], Format = 0x01):
        self.Attributes = Attributes
        self.Format = Format & 0xFF

    def build(self):
        data = []
        for attribute in self.Attributes:
            tmpdata = []
            tmpdata += data + Utilities.littleEndian(attribute.handle)
            tmpdata += Utilities.littleEndian(attribute.uuid)
            if len(tmpdata) <= ATT_MTU - 2:
                data = tmpdata
            else:
                raise Exception,"Packet length exceed MTU"
        self.Content = [self.Opcode, self.Format] + data

    def parse(self, packet):
        size = len(packet)
        self.Format = self.Content[1]
        self.Attributes = []
        size = size - 2;
        if self.Format == format['TYPE_16']:
            index = 2
            while size >= 4:
                handle = (self.Content[index+1]<<8) | self.Content[index]
                uuid = (self.Content[index+3]<<8) | self.Content[index+2]
                self.Attributes.append(Attribute(handle, uuid, None))
                size = size - 4
                index = index + 4
        elif self.Format == format['TYPE_128']:
            handle = (self.Content[3] << 8) | self.Content[2]
            temp = self.Content[4:]
            temp.reverse()
            uuid = 0
            for value in temp:
                uuid = (uuid << 8) | value
            self.Attributes.append(Attribute(handle, uuid, None))

class AttFindByTypeValueRequest(AttRequest):
    def create(self, StartHdl = 0x0001, EndHdl = 0xFFFF, AttributeType = 0x0000, AttributeValue = []):
        self.StartHdl = StartHdl & 0xFFFF
        self.EndHdl = EndHdl & 0xFFFF
        self.AttributeType = AttributeType & 0xFFFF
        self.AttributeValue = [int(el) & 0xFF for el in AttributeValue]

    def build(self):
        self.Content = [self.Opcode,
            self.StartHdl & 0xFF, (self.StartHdl >> 8) & 0xFF,
            self.EndHdl & 0xFF, (self.EndHdl >> 8) & 0xFF,
            self.AttributeType & 0xFF, (self.AttributeType >> 8) & 0xFF] + self.AttributeValue

    def parse(self, packet):
        self.StartHdl       = (self.Content[2] << 8) | self.Content[1]
        self.EndHdl         = (self.Content[4] << 8) | self.Content[3]
        self.AttributeType  = (self.Content[6] << 8) | self.Content[5]
        self.AttributeValue = self.Content[7:]

class AttFindByTypeValueResponse(AttResponse):
    def create(self, FoundHandles = []):
        self.FoundHandles = FoundHandles

    def build(self):
        data = []
        for attribute in self.FoundHandles:
            tmpdata = []
            tmpdata += data + Utilities.littleEndian(attribute.foundHandle)
            tmpdata += Utilities.littleEndian(attribute.endFoundHandle)
            if len(tmpdata) <= ATT_MTU - 1:
                data = tmpdata
            else:
                raise Exception,"Packet length exceed MTU"
        self.Content = [self.Opcode] + data

    def parse(self, packet):
        size = len(packet)
        self.FoundHandles   = []
        for index in range(((size-1)/4)):
            FoundHandle = (self.Content[(index*4)+2] << 8) | self.Content[(index*4)+1]
            EndHandle = (self.Content[(index*4)+4] << 8) | self.Content[(index*4)+3]
            self.FoundHandles.append(AttributeFound(FoundHandle,EndHandle))

class AttReadByTypeRequest(AttRequest):
    def create(self, StartHdl = 0x0001, EndHdl = 0xFFFF,  UUID = 0x0000):
        self.StartHdl = StartHdl & 0xFFFF
        self.EndHdl = EndHdl & 0xFFFF
        self.UUID = UUID

    def build(self):
        self.Content = [self.Opcode,
            self.StartHdl & 0xFF, (self.StartHdl >> 8) & 0xFF,
            self.EndHdl & 0xFF, (self.EndHdl >> 8) & 0xFF] + Utilities.littleEndian(self.UUID)

    def parse(self, packet):
        self.StartHdl = (self.Content[2] << 8) | self.Content[1]
        self.EndHdl = (self.Content[4] << 8) | self.Content[3]
        self.UUID = 0
        temp = self.Content[5:]
        temp.reverse()
        for value in temp:
            self.UUID = (self.UUID << 8) | value

class AttReadByTypeResponse(AttResponse):
    def create(self, Length = 0, Attributes = []):
        self.Length = Length & 0xFF
        self.Attributes = Attributes

    def build(self):
        data = []
        for attribute in self.Attributes:
            tmpdata  = []
            tmpdata += data + Utilities.littleEndian(attribute.handle)
            tmpdata += attribute.value
            if len(tmpdata) <= ATT_MTU - 2:
                data = tmpdata
            else:
                raise Exception,"Packet length exceed MTU"
        self.Content = [self.Opcode, self.Length] + data

    def parse(self, packet):
        self.Length = self.Content[1]
        size = len(self.Content[2:])
        index = 2
        self.Attributes = []
        while size >= self.Length and index+self.Length <= len(packet):
            handle = (self.Content[index+1] << 8) | self.Content[index]
            value = self.Content[index+2:index+self.Length]
            index += self.Length
            size -= self.Length
            self.Attributes.append(Attribute(handle,None,value))

class AttReadRequest(AttRequest):
    def create(self, Handle = 0x0000):
        self.Handle = Handle & 0xFFFF

    def build(self):
        self.Content = [self.Opcode] + Utilities.littleEndian(self.Handle)

    def parse(self, packet):
        self.Handle = (self.Content[2] << 8) | self.Content[1]

class AttReadResponse(AttResponse):
    def create(self, Attributes = None):
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode] + self.Attributes.value[:ATT_MTU]

    def parse(self, packet):
        value = self.Content[1:]
        self.Attributes = Attribute(None,None,value)

class AttReadBlobRequest(AttRequest):
    def create(self, Handle = 0x000, Offset = 0):
        self.Handle = Handle
        self.Offset = Offset & 0xFFFF

    def build(self):
        self.Content = [self.Opcode] + Utilities.littleEndian(self.Handle) + Utilities.littleEndian(self.Offset)

    def parse(self, packet):
        self.Handle = (self.Content[2] << 8) | self.Content[1]
        self.Offset = (self.Content[4] << 8) | self.Content[3]

class AttReadBlobResponse(AttResponse):
    def create(self, Attributes = None, Offset = 0):
        self.Attributes = Attributes
        self.Offset = Offset

    def build(self):
        self.Content = [self.Opcode] + self.Attributes.value[self.Offset:self.Offset + ATT_MTU - 1]

    def parse(self, packet):
        value = self.Content[1:]
        self.Attributes = Attribute(None,None,value)


class AttReadByGroupTypeRequest(AttRequest):
    def create(self, StartingHandle = 0x0001, EndingHandle = 0xFFFF, Type = 0x0000):
        self.StartingHandle = StartingHandle & 0xFFFF
        self.EndingHandle = EndingHandle & 0xFFFF
        self.Type = Type & 0xFFFF

    def build(self):
        self.Content = [self.Opcode] + Utilities.littleEndian(self.StartingHandle) + Utilities.littleEndian(self.EndingHandle) + Utilities.littleEndian(self.Type)

    def parse(self, packet):
        self.StartingHandle = (packet[2] << 8) | packet[1]
        self.EndingHandle   = (packet[4] << 8) | packet[3]
        self.Type           = (packet[6] << 8) | packet[5]

class AttReadByGroupTypeResponse(AttResponse):
    def create(self, Length = 0, Attributes = []):
        self.Length = Length & 0xFF
        self.Attributes = Attributes

    def build(self):
        data = []
        for attribute in self.Attributes:
            tmpdata  = []
            tmpdata += data
            tmpdata += Utilities.littleEndian(attribute.handle)
            tmpdata += Utilities.littleEndian(attribute.endHandle)
            tmpdata += attribute.value
            if len(tmpdata) <= ATT_MTU - 2:
                data = tmpdata
            else:
                raise Exception,"Packet length exceed MTU"
        self.Content = [self.Opcode, self.Length] + data

    def parse(self, packet):
        size = len(packet)
        pos = 1
        self.Groups = []
        self.GroupLen = packet[1]
        for index in range(((size-2)/self.GroupLen)):
            FoundHandle = (self.Content[(index*self.GroupLen)+3] << 8) | self.Content[(index*self.GroupLen)+2]
            EndHandle = (self.Content[(index*self.GroupLen)+5] << 8) | self.Content[(index*self.GroupLen)+4]
            value = self.Content[(index*self.GroupLen)+6:(index*self.GroupLen)+self.GroupLen+2]
            self.Groups.append(AttributeFound(FoundHandle,EndHandle,value))

class AttWriteCommand(AttCommand):
    def create(self, Attributes = None):
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode, self.Attributes.handle & 0xFF, (self.Attributes.handle >> 8) & 0xFF] + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[3:]
        self.Attributes = Attribute(handle,None,value)

class AttSignedWriteCommand(AttCommand):
    def create(self, Attributes = None, Signature = []):
        self.Attributes = Attributes
        self.Signature = Signature
        if len(Signature) == 12:
            self.Counter    = int("".join("{0:02X}".format(el) for el in self.Signature[3::-1]),16)
            self.Cmac       = self.Signature[4:]

    def addSignature(self, Signature):
        self.Signature = Signature
        if len(Signature) == 12:
            self.Counter    = int("".join("{0:02X}".format(el) for el in self.Signature[3::-1]),16)
            self.Cmac       = self.Signature[4:]
        self.build()

    def build(self):
        self.Content = [self.Opcode, self.Attributes.handle & 0xFF, (self.Attributes.handle >> 8) & 0xFF] + self.Attributes.value + [int(el) for el in self.Signature[0:12]]

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[3:]
        self.Attributes = Attribute(handle,None,value)
        self.Signature  = self.Content[-12::]
        self.Counter    = int("".join("{0:02X}".format(el) for el in self.Signature[3::-1]),16)
        self.Cmac       = self.Signature[4:]

class AttWriteRequest(AttRequest):
    def create(self, Attributes = None):
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode, self.Attributes.handle & 0xFF, (self.Attributes.handle >> 8) & 0xFF] + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[3:]
        self.Attributes = Attribute(handle,None,value)

class AttWriteResponse(AttResponse):
    def build(self):
        self.Content = [self.Opcode]

    def parse(self, packet):
        self.Opcode = self.Content[0] & 0x7F

class AttPrepareWriteRequest(AttRequest):
    def create(self, Attributes = None, Offset = 0):
        self.Attributes = Attributes
        self.Offset = Offset & 0xFFFF

    def build(self):
        self.Content = [self.Opcode] + Utilities.littleEndian(self.Attributes.handle & 0xFFFF) + Utilities.littleEndian(self.Offset) + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[5:]
        self.Attributes = Attribute(handle, None, value)
        self.Offset = (self.Content[4] << 8) | self.Content[3]

class AttPrepareWriteResponse(AttResponse):
    def create(self, Attributes = None, Offset = 0):
        self.Attributes = Attributes
        self.Offset = Offset

    def build(self):
        self.Content = [self.Opcode] + Utilities.littleEndian(self.Attributes.handle & 0xFFFF) + Utilities.littleEndian(self.Offset) + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[5:]
        self.Attributes = Attribute(handle, None, value)
        self.Offset = (self.Content[4] << 8) | self.Content[3]

class AttExecuteWriteRequest(AttRequest):
    def create(self, Flags = 0x01, Attributes = None):
        self.Flags = Flags & 0xFF
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode, self.Flags & 0xFF]

    def parse(self, packet):
        self.Flags = self.Content[1]

class AttExecuteWriteResponse(AttResponse):
    def build(self):
        self.Content = [self.Opcode]

    def parse(self, packet):
        self.Opcode = self.Content[0] & 0x7F


class AttHandleValueNotification(AttNotification):
    def create(self, Attributes = None):
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode, self.Attributes.handle & 0xFF, (self.Attributes.handle >> 8) & 0xFF] + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[3:]
        self.Attributes = Attribute(handle,None,value)

class AttHandleValueIndication(AttIndication):
    def create(self, Attributes = None):
        self.Attributes = Attributes

    def build(self):
        self.Content = [self.Opcode, self.Attributes.handle & 0xFF, (self.Attributes.handle >> 8) & 0xFF] + self.Attributes.value

    def parse(self, packet):
        handle = (self.Content[2] << 8) | self.Content[1]
        value = self.Content[3:]
        self.Attributes = Attribute(handle,None,value)

class AttHandleValueConfirmation(AttConfirmation):
    def build(self):
        self.Content = [self.Opcode]

ATT_MTU = 23
BT_BASE_UUID = 0x0000000000001000800000805F9B34FB

packets = {
    'ERROR_RESPONSE'                :{'Opcode':0x01,'Pkt':AttErrorResponse,'minSize':5, 'maxSize':5},
    ## Server Configuration
    'EXCHANGE_MTU_REQUEST'          :{'Opcode':0x02,'Pkt':AttExchangeMtuRequest,'minSize':3, 'maxSize':3},
    'EXCHANGE_MTU_RESPONSE'         :{'Opcode':0x03,'Pkt':AttExchangeMtuResponse,'minSize':3, 'maxSize':3},
    ## Discovery
    'FIND_INFORMATION_REQUEST'      :{'Opcode':0x04,'Pkt':AttFindInformationRequest,'minSize':5, 'maxSize':5},
    'FIND_INFORMATION_RESPONSE'     :{'Opcode':0x05,'Pkt':AttFindInformationResponse,'minSize':6, 'maxSize':ATT_MTU},
    'FIND_BY_TYPE_VALUE_REQUEST'    :{'Opcode':0x06,'Pkt':AttFindByTypeValueRequest,'minSize':7, 'maxSize':ATT_MTU},
    'FIND_BY_TYPE_VALUE_RESPONSE'   :{'Opcode':0x07,'Pkt':AttFindByTypeValueResponse,'minSize':5, 'maxSize':ATT_MTU},
    ## Read
    'READ_BY_TYPE_REQUEST'          :{'Opcode':0x08,'Pkt':AttReadByTypeRequest,'minSize':7, 'maxSize':21},
    'READ_BY_TYPE_RESPONSE'         :{'Opcode':0x09,'Pkt':AttReadByTypeResponse,'minSize':4, 'maxSize':ATT_MTU},
    'READ_REQUEST'                  :{'Opcode':0x0A,'Pkt':AttReadRequest,'minSize':3, 'maxSize':3},
    'READ_RESPONSE'                 :{'Opcode':0x0B,'Pkt':AttReadResponse,'minSize':1, 'maxSize':ATT_MTU},
    'READ_BLOB_REQUEST'             :{'Opcode':0x0C,'Pkt':AttReadBlobRequest,'minSize':5, 'maxSize':5},
    'READ_BLOB_RESPONSE'            :{'Opcode':0x0D,'Pkt':AttReadBlobResponse,'minSize':1, 'maxSize':ATT_MTU},
    # 'READ_MULTIPLE_REQUEST'         :{'Opcode':0x0E,'Pkt':AttReadMultipleRequest,'minSize':5, 'maxSize':ATT_MTU},
    # 'READ_MULTIPLE_RESPONSE'        :{'Opcode':0x0F,'Pkt':AttReadMultipleResponse,'minSize':1, 'maxSize':ATT_MTU},
    'READ_BY_GROUP_TYPE_REQUEST'    :{'Opcode':0x10,'Pkt':AttReadByGroupTypeRequest,'minSize':7, 'maxSize':21},
    'READ_BY_GROUP_TYPE_RESPONSE'   :{'Opcode':0x11,'Pkt':AttReadByGroupTypeResponse,'minSize':5, 'maxSize':ATT_MTU},
    ## Write
    'WRITE_COMMAND'                 :{'Opcode':0x52,'Pkt':AttWriteCommand,'minSize':3, 'maxSize':ATT_MTU},
    'SIGNED_WRITE_COMMAND'          :{'Opcode':0xD2,'Pkt':AttSignedWriteCommand,'minSize':3, 'maxSize':ATT_MTU},
    'WRITE_REQUEST'                 :{'Opcode':0x12,'Pkt':AttWriteRequest,'minSize':3, 'maxSize':ATT_MTU},
    'WRITE_RESPONSE'                :{'Opcode':0x13,'Pkt':AttWriteResponse,'minSize':1, 'maxSize':1},
    'PREPARE_WRITE_REQUEST'         :{'Opcode':0x16,'Pkt':AttPrepareWriteRequest,'minSize':5, 'maxSize':ATT_MTU},
    'PREPARE_WRITE_RESPONSE'        :{'Opcode':0x17,'Pkt':AttPrepareWriteResponse,'minSize':5, 'maxSize':ATT_MTU},
    'EXECUTE_WRITE_REQUEST'         :{'Opcode':0x18,'Pkt':AttExecuteWriteRequest,'minSize':2, 'maxSize':2},
    'EXECUTE_WRITE_RESPONSE'        :{'Opcode':0x19,'Pkt':AttExecuteWriteResponse,'minSize':1, 'maxSize':1},
    ## Server Initiated
    'HANDLE_VALUE_NOTIFICATION'     :{'Opcode':0x1B,'Pkt':AttHandleValueNotification,'minSize':3, 'maxSize':ATT_MTU},
    'HANDLE_VALUE_INDICATION'       :{'Opcode':0x1D,'Pkt':AttHandleValueIndication,'minSize':3, 'maxSize':ATT_MTU},
    'HANDLE_VALUE_CONFIRMATION'     :{'Opcode':0x1E,'Pkt':AttHandleValueConfirmation,'minSize':1, 'maxSize':1},
}
opcodeLookup = dict([value['Opcode'],{'Name':key,'Pkt':value['Pkt'],'minSize':value['minSize'],'maxSize':value['maxSize']}] for key,value in packets.iteritems() if 'Pkt' in value)
pktLookup = dict([value['Pkt'],{'Name':key,'Opcode':value['Opcode']}] for key,value in packets.iteritems() if 'Pkt' in value)

errorCode = {
    'INVALID_HANDLE'                : 0x01,
    'READ_NOT_PERMITTED'            : 0x02,
    'WRITE_NOT_PERMITTED'           : 0x03,
    'INVALID_PDU'                   : 0x04,
    'INSUFFICIENT_AUTHENTICATION'   : 0x05,
    'REQUEST_NOT_SUPPORTED'         : 0x06,
    'INVALID_OFFSET'                : 0x07,
    'INSUFFICIENT_AUTHORIZATION'    : 0x08,
    'PREPARE_QUEUE_FULL'            : 0x09,
    'ATTRIBUTE_NOT_FOUND'           : 0x0A,
    'ATTRIBUTE_NOT_LONG'            : 0x0B,
    'INSUFFICIENT_ENC_KEY_SIZE'     : 0x0C,
    'INVALID_ATTRIBUTE_VALUE_LEN'   : 0x0D,
    'UNLIKELY_ERROR'                : 0x0E,
    'INSUFFICIENT_ENCRYPTION'       : 0x0F,
    'UNSUPPORTED_GROUP_TYPE'        : 0x10,
    'INSUFFICIENT_RESOURCES'        : 0x11,
    'APPLICATION_ERROR_STRT'        : 0x80,
    'CCCD_IMPROPERLY_CONFIGURED'    : 0xFD,
    'PROCEDURE_ALREADY_IN_PROGRESS' : 0xFE,
    'APPLICATION_ERROR_END'         : 0xFF,
    # proprietary command
    'DEFERRAL_REQUIRED'             : 0x40,
}
format = {
    'TYPE_16'   : 0x01,
    'TYPE_128'  : 0x02,
}

