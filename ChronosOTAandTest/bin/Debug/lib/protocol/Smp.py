#! /usr/bin/python
from modules.common import DefaultPktFunctions, Utilities
# import Exceptions
from modules.common import PacketLengthError

class SmpPkt(DefaultPktFunctions):
    EventCode = 0x93
    def __new__(clr, *args, **argv):
        if ('packet' in argv and clr == SmpPkt):
            # Check if the Code is in the valid codes
            if argv['packet'][0] in opcodeLookup:
                # Fetching the packet type to generate
                packetType = opcodeLookup[argv['packet'][0]]['Pkt']
                
                # Checking if the packet size is within the valid bounds
                if len(argv['packet']) != opcodeLookup[argv['packet'][0]]['pktSize']:
                    # if the packet is outside the valid bounds, return an PacketLengthError
                    raise PacketLengthError(packetType,argv['packet'])
                
                # Generate and return the correct packet type
                return super(SmpPkt, packetType).__new__(packetType)
            # If the opcode were not in the "known" packet list, return a General SMP Packet
            return super(SmpPkt, GeneralSmpPacket).__new__(GeneralSmpPacket)
        
        # The packet type to construct is know, noo need to find the Packet Type to construct
        return super(SmpPkt,clr).__new__(clr)
        
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
            
    def __deepcopy__(self, memo):
        # Added as workaround for exception when trying to do a deepcopy of a 
        # dict that contains an instance of this class or subclasses
        return self
    
    def parse(self, packet):
        pass
    def create(self, *args, **argv):
        pass
    def build(self):
        pass

class GeneralSmpPacket(SmpPkt):
    def parse(self, packet):
        pass

class SmpRequest(SmpPkt):
    pass

class SmpSlaveRequest(SmpPkt):
    EventCode = 0x90 #SerialCommTypeMapping.TypeToEventCode[SerialComm.SMP_REQUEST]

class SmpResponse(SmpPkt):
    pass
        
class SmpPairingReserved0(SmpPkt):
    def create(self):
        pass
    
    def build(self):
        self.Content = [self.Opcode]
    
    def parse(self,packet):
        pass

class SmpPairingRequest(SmpRequest):
    def create(self, IoCapability = 0x03, OobDataFlag = 0x00, Bonding = False, Mitm = False, MaxEncKeySize = 16, MKeyDistrBitmap = 0x00, SKeyDistrBitmap = 0x00):
        self.IoCapability   = IoCapability & 0xFF
        self.OobDataFlag    = OobDataFlag & 0xFF
        self.Bonding        = Bonding == True
        self.Mitm           = Mitm == True
        self.MaxEncKeySize  = MaxEncKeySize & 0xFF
        self.MKeyDistrBitmap= MKeyDistrBitmap & 0xFF
        self.SKeyDistrBitmap= SKeyDistrBitmap & 0xFF
        
    def build(self):
        self.Content = [self.Opcode, 
            self.IoCapability,
            self.OobDataFlag,
            ([0,authReqBits['MITM']][self.Mitm]|[0,authReqBits['Bonding']][self.Bonding]),
            self.MaxEncKeySize,
            self.MKeyDistrBitmap,self.SKeyDistrBitmap]
    
    def parse(self,packet):
        size = len(packet)
        self.IoCapability   = self.Content[1]
        self.OobDataFlag    = self.Content[2]
        self.Bonding        = (self.Content[3] & authReqBits['Bonding']) != 0
        self.Mitm           = (self.Content[3] & authReqBits['MITM']) != 0
        self.MaxEncKeySize  = self.Content[4]
        self.MKeyDistrBitmap= self.Content[5]
        self.SKeyDistrBitmap= self.Content[6]

class SmpPairingResponse(SmpResponse):
    def create(self, IoCapability = 0x03, OobDataFlag = 0x00, Bonding = False, Mitm = False, MaxEncKeySize = 16, MKeyDistrBitmap = 0x00, SKeyDistrBitmap = 0x00):
        self.IoCapability   = IoCapability & 0xFF
        self.OobDataFlag    = OobDataFlag & 0xFF
        self.Bonding        = Bonding == True
        self.Mitm           = Mitm == True
        self.MaxEncKeySize  = MaxEncKeySize & 0xFF
        self.MKeyDistrBitmap= MKeyDistrBitmap & 0xFF
        self.SKeyDistrBitmap= SKeyDistrBitmap & 0xFF
        
    def build(self):
        self.Content = [self.Opcode, 
            self.IoCapability,
            self.OobDataFlag,
            ([0,authReqBits['MITM']][self.Mitm]|[0,authReqBits['Bonding']][self.Bonding]),
            self.MaxEncKeySize,
            self.MKeyDistrBitmap,self.SKeyDistrBitmap]
    
    def parse(self,packet):
        size = len(packet)
        self.IoCapability   = self.Content[1]
        self.OobDataFlag    = self.Content[2]
        self.Bonding        = (self.Content[3] & authReqBits['Bonding']) != 0
        self.Mitm           = (self.Content[3] & authReqBits['MITM']) != 0
        self.MaxEncKeySize  = self.Content[4]
        self.MKeyDistrBitmap= self.Content[5]
        self.SKeyDistrBitmap= self.Content[6]

class SmpPairingConfirm(SmpPkt):
    def create(self, ConfirmLtlEndArray = None, ConfirmValue = None):
        if ConfirmLtlEndArray != None:
            self.ConfirmLtlEndArray = ConfirmLtlEndArray
            if ConfirmValue == None:
                self.ConfirmValue = int("".join("%02X" % el for el in self.ConfirmLtlEndArray[-1::-1]),16)
        if ConfirmValue != None:
            self.ConfirmValue = ConfirmValue
            if ConfirmLtlEndArray == None:
                self.ConfirmLtlEndArray = Utilities.littleEndian(self.ConfirmValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode] + self.ConfirmLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.ConfirmLtlEndArray = [el for el in self.Content[1:]]
        self.ConfirmValue = int("".join("%02X" % el for el in self.ConfirmLtlEndArray[-1::-1]),16)
        
class SmpPairingRandom(SmpPkt):
    def create(self, RandomLtlEndArray = None, RandomValue = None):
        if RandomLtlEndArray != None:
            self.RandomLtlEndArray = RandomLtlEndArray
            if RandomValue == None:
                self.RandomValue = int("".join("%02X" % el for el in self.RandomLtlEndArray[-1::-1]),16)
        if RandomValue != None:
            self.RandomValue = RandomValue
            if RandomLtlEndArray == None:
                self.RandomLtlEndArray = Utilities.littleEndian(self.RandomValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode] + self.RandomLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.RandomLtlEndArray = [el for el in self.Content[1:]]
        self.RandomValue = int("".join("%02X" % el for el in self.RandomLtlEndArray[-1::-1]),16)
    
class SmpPairingFailed(SmpPkt):
    def create(self, Reason = 0x00):
        self.Reason = Reason & 0xFF
    
    def build(self):
        self.Content = [self.Opcode, self.Reason]
    
    def parse(self,packet):
        size = len(packet)
        self.Reason = self.Content[1]

class SmpEncryptionInformation(SmpPkt):
    def create(self, LtkLtlEndArray = None, LtkValue = None):
        if LtkLtlEndArray != None:
            self.LtkLtlEndArray = LtkLtlEndArray
            if LtkValue == None:
                self.LtkValue = int("".join("%02X" % el for el in self.LtkLtlEndArray[-1::-1]),16)
        if LtkValue != None:
            self.LtkValue = LtkValue
            if LtkLtlEndArray == None:
                self.LtkLtlEndArray = Utilities.littleEndian(self.LtkValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode] + self.LtkLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.LtkLtlEndArray = [el for el in self.Content[1:]]
        self.LtkValue = int("".join("%02X" % el for el in self.LtkLtlEndArray[-1::-1]),16)
        
class SmpMasterIdentification(SmpPkt):
    def create(self, RandLtlEndArray = None, RandValue = None, EdivLtlEndArray = None, EdivValue = None):
        if RandLtlEndArray != None:
            self.RandLtlEndArray = RandLtlEndArray
            if RandValue == None:
                self.RandValue = int("".join("%02X" % el for el in self.RandLtlEndArray[-1:2:-1]),16)
        if RandValue != None:
            self.RandValue = RandValue
            if RandLtlEndArray == None:
                self.RandLtlEndArray = Utilities.littleEndian(self.RandValue,byte=8)
        if EdivLtlEndArray != None:
            self.EdivLtlEndArray = EdivLtlEndArray
            if EdivValue == None:
                self.EdivValue = int("".join("%02X" % el for el in self.EdivLtlEndArray[2:0:-1]),16)
        if EdivValue != None:
            self.EdivValue = EdivValue
            if EdivLtlEndArray == None:
                self.EdivLtlEndArray = Utilities.littleEndian(self.EdivValue,byte=2)
    
    def build(self):
        self.Content = [self.Opcode] + self.EdivLtlEndArray + self.RandLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.EdivLtlEndArray = [el for el in self.Content[1:3]]
        self.EdivValue = int("".join("%02X" % el for el in self.EdivLtlEndArray[-1::-1]),16)
        self.RandLtlEndArray = [el for el in self.Content[3:]]
        self.RandValue = int("".join("%02X" % el for el in self.RandLtlEndArray[-1::-1]),16)

class SmpIdentityInformation(SmpPkt):
    def create(self, IrkLtlEndArray = None, IrkValue = None):
        if IrkLtlEndArray != None:
            self.IrkLtlEndArray = IrkLtlEndArray
            if IrkValue == None:
                self.IrkValue = int("".join("%02X" % el for el in self.IrkLtlEndArray[-1::-1]),16)
        if IrkValue != None:
            self.IrkValue = IrkValue
            if IrkLtlEndArray == None:
                self.IrkLtlEndArray = Utilities.littleEndian(self.IrkValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode] + self.IrkLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.IrkLtlEndArray = [el for el in self.Content[1:]]
        self.IrkValue = int("".join("%02X" % el for el in self.IrkLtlEndArray[-1::-1]),16)

class SmpIdentityAddressInformation(SmpPkt):
    def create(self, AddrType=None, AddrLtlEndArray = None, AddrValue = None):
        self.AddrType = AddrType
        if AddrLtlEndArray != None:
            self.AddrLtlEndArray = AddrLtlEndArray
            if AddrValue == None:
                self.AddrValue = int("".join("%02X" % el for el in self.AddrLtlEndArray[-1::-1]),16)
        if AddrValue != None:
            self.AddrValue = AddrValue
            if AddrLtlEndArray == None:
                self.AddrLtlEndArray = Utilities.littleEndian(self.AddrValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode, self.AddrType] + self.AddrLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        self.AddrType = self.Content[1]
        self.AddrLtlEndArray = [el for el in self.Content[2:]]
        self.AddrValue = int("".join("%02X" % el for el in self.AddrLtlEndArray[-1::-1]),16)

class SmpSigningInformation(SmpPkt):
    def create(self, SrkLtlEndArray = None, SrkValue = None):
        if SrkLtlEndArray != None:
            self.SrkLtlEndArray = SrkLtlEndArray
            if SrkValue == None:
                self.SrkValue = int("".join("%02X" % el for el in self.SrkLtlEndArray[-1::-1]),16)
        if SrkValue != None:
            self.SrkValue = SrkValue
            if SrkLtlEndArray == None:
                self.SrkLtlEndArray = Utilities.littleEndian(self.SrkValue,byte=16)
    
    def build(self):
        self.Content = [self.Opcode] + self.SrkLtlEndArray
    
    def parse(self,packet):
        size = len(packet)
        if size >= 17:
            self.SrkLtlEndArray = [el for el in self.Content[1:]]
            self.SrkValue = int("".join("%02X" % el for el in self.SrkLtlEndArray[-1::-1]),16)
        
class SmpSecurityRequest(SmpSlaveRequest):
    def create(self, Bonding = True, Mitm = False):
        self.Bonding        = Bonding == True
        self.Mitm           = Mitm == True
        
    def build(self):
        self.Content = [self.Opcode,
            ([0,authReqBits['MITM']][self.Bonding]|[0,authReqBits['Bonding']][self.Mitm])]
    
    def parse(self,packet):
        size = len(packet)
        self.Mitm = None
        self.Bonding = None
        self.Bonding        = (packet[1] & authReqBits['Bonding']) != 0
        self.Mitm           = (packet[1] & authReqBits['MITM']) != 0

packets = {
    ## Pairing Methods
    'PAIRING_RESERVED0'         :{'Opcode':0x00,'Pkt':SmpPairingReserved0,'pktSize':1},
    'PAIRING_REQUEST'           :{'Opcode':0x01,'Pkt':SmpPairingRequest,'pktSize':7},
    'PAIRING_RESPONSE'          :{'Opcode':0x02,'Pkt':SmpPairingResponse,'pktSize':7},
    'PAIRING_CONFIRM'           :{'Opcode':0x03,'Pkt':SmpPairingConfirm,'pktSize':17},
    'PAIRING_RANDOM'            :{'Opcode':0x04,'Pkt':SmpPairingRandom,'pktSize':17},
    'PAIRING_FAILED'            :{'Opcode':0x05,'Pkt':SmpPairingFailed,'pktSize':2},
    ## Security in BLE
    'ENCRYPTION_INFORMATION'    :{'Opcode':0x06,'Pkt':SmpEncryptionInformation,'pktSize':17},
    'MASTER_IDENTIFICATION'     :{'Opcode':0x07,'Pkt':SmpMasterIdentification,'pktSize':11},
    'IDENTITY_INFORMATION'      :{'Opcode':0x08,'Pkt':SmpIdentityInformation,'pktSize':17},
    'IDENTITY_ADDRESS_INFO'     :{'Opcode':0x09,'Pkt':SmpIdentityAddressInformation,'pktSize':8},
    'SIGNING_INFORMATION'       :{'Opcode':0x0A,'Pkt':SmpSigningInformation,'pktSize':17},
    'SECURITY_REQUEST'          :{'Opcode':0x0B,'Pkt':SmpSecurityRequest,'pktSize':2},
}
opcodeLookup = dict([value['Opcode'],{'Name':key,'Pkt':value['Pkt'],'pktSize':value['pktSize']}] for key,value in packets.iteritems() if 'Pkt' in value)
pktLookup = dict([value['Pkt'],{'Name':key,'Opcode':value['Opcode']}] for key,value in packets.iteritems() if 'Pkt' in value)


errorCodes = {
    'Passkey Entry Failed'          :0x01,
    'OOB Not Available'             :0x02,
    'Authentication Requirements'   :0x03,
    'Confirm Value Failed'          :0x04,
    'Pairing Not Supported'         :0x05,
    'Encryption Key Size'           :0x06,
    'Command Not Supported'         :0x07,
    'Unspecified Reason'            :0x08,
    'Repeated Attempts'             :0x09,
    'Invalid Paramters'             :0x0A,
}

ioCapabilities = {
    'Display Only'      :0x00,
    'Display Yes No'    :0x01,
    'Keyboard Only'     :0x02,
    'No Input No Output':0x03,
    'Keyboard Display'  :0x04,
}

oobData = {
    'OOB Auth not present'  :0x00,
    'OOB Auth present'      :0x01,
}

authReqBits = {
    'No Bonding'    :0x00,
    'Bonding'       :0x01,
    'MITM'          :0x04,
}

keyDistributionBits = {
    'EncKey'    :0x01,
    'IdKey'     :0x02,
    'SignKey'   :0x04,
}