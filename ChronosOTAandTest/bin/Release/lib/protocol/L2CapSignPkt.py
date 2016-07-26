#! /usr/bin/python
from modules.common import DefaultPktFunctions, Utilities
# import Exceptions
from modules.common import PacketLengthError

class L2CapSignalingPkt(DefaultPktFunctions):
    EventCode = 0x8F
    def __new__(clr, *args, **argv):
        if ('packet' in argv and clr == L2CapSignalingPkt):
            # Check if the Code is in the valid codes
            code = argv['packet'][0]
            if code in opcodeLookup:
                # Fetching the packet type to generate
                packetType = opcodeLookup[code]['Pkt']
                # Checking if the packet size is within the valid bounds
                if not opcodeLookup[code]['minSize'] <= len(argv['packet']) <= opcodeLookup[code]['maxSize']:
                    # if the packet is outside the valid bounds, return an PacketLengthError
                    raise PacketLengthError(packetType,argv['packet'])
                
                # Generate and return the correct packet type
                return super(L2CapSignalingPkt, packetType).__new__(packetType)
            # If the code were not in the "known" packet list, return a General L2CapSignaling Packet
            return super(L2CapSignalingPkt, GeneralL2CapSignalingPacket).__new__(GeneralL2CapSignalingPacket)
        
        # The packet type to construct is know, noo need to find the Packet Type to construct
        return super(L2CapSignalingPkt,clr).__new__(clr)
        
    def __init__(self, *args, **argv):
        self.Content = []
        # If 'packet' is in the argv, we know it has to be parsed (all classes need to implement create, build and parse)
        if 'packet' in argv:
            packet = argv['packet']
            # Putting the packet inside the Content of the Class
            self.Content = [int(el) for el in packet]
            # Defining the code of the Class
            self.Code       = packet[0]
            self.Identifier = packet[1]
            self.Length     = (packet[2] | (packet[3] << 8))
            # Parsing the packet
            self.parse(packet)
        else:
            # It was a known packet, let's fetch the Code for it
            self.Code = [None,pktLookup[self.__class__]['Code']][self.__class__ in pktLookup]
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

class GeneralL2CapSignalingPacket(L2CapSignalingPkt):
    pass

class L2CapCommandReject(L2CapSignalingPkt):
    def create(self, Identifier = 0x00, Reason = 0x0000, Data = [], Length = None):
        self.Identifier = Identifier
        self.Reason = Reason & 0xFFFF
        self.Data   = [int(el) for el in Data]
        self.Length = 2 + len(self.Data)
        if Length != None:
            self.Length = Length
    
    def build(self):
        self.Content = [self.Code, self.Identifier] + Utilities.littleEndian(self.Length) + Utilities.littleEndian(self.Reason) + self.Data
        
    def parse(self, packet):
        self.Reason         = (packet[5] << 8) | packet[4]
        self.Data           = packet[6:]
        
class L2CapInformationRequest(L2CapSignalingPkt):
    def create(self, Identifier = 0x00, InfoType = 0x0000, Length = None):
        self.Identifier = Identifier
        self.InfoType   = InfoType & 0xFFFF
        self.Length     = 2 
        if Length != None:
            self.Length = Length
    
    def build(self):
        self.Content = [self.Code, self.Identifier] + Utilities.littleEndian(self.Length) + Utilities.littleEndian(self.InfoType)
    
    def parse(self, packet):
        self.InfoType    = (packet[5] << 8) | packet[4]

class L2CapConnectionParameterUpdateRequest(L2CapSignalingPkt):
    def create(self, Identifier = 0x00, IntervalMin = 0x0006, IntervalMax = 0x0050, SlaveLatency = 0x0000, TimeoutMultiplier = 0x0250, Length = None):
        self.Identifier         = Identifier
        self.IntervalMin        = IntervalMin & 0xFFFF
        self.IntervalMax        = IntervalMax & 0xFFFF
        self.SlaveLatency       = SlaveLatency & 0xFFFF
        self.TimeoutMultiplier  = TimeoutMultiplier & 0xFFFF
        self.Length     = 8
        if Length != None:
            self.Length = Length
    
    def build(self):
        self.Content = ([self.Code, self.Identifier] + 
            Utilities.littleEndian(self.Length) +
            Utilities.littleEndian(self.IntervalMin) +
            Utilities.littleEndian(self.IntervalMax) +
            Utilities.littleEndian(self.SlaveLatency) +
            Utilities.littleEndian(self.TimeoutMultiplier))
    
    def parse(self, packet):
        self.IntervalMin    = (packet[5] << 8) | packet[4]
        self.IntervalMax    = (packet[7] << 8) | packet[6]
        self.SlaveLatency   = (packet[9] << 8) | packet[8]
        self.TimeoutMultiplier   = (packet[11] << 8) | packet[10]
        
class L2CapConnectionParameterUpdateResponse(L2CapSignalingPkt):
    def create(self, Identifier = 0x00, Result = 0x0000, Length = None):
        self.Identifier = Identifier
        self.Result = Result & 0xFFFF
        self.Length = 2
        if Length != None:
            self.Length = Length
    
    def build(self):
        self.Content = [self.Code, self.Identifier] + Utilities.littleEndian(self.Length) + Utilities.littleEndian(self.Result)
        
    def parse(self, packet):
        self.Reason         = (packet[5] << 8) | packet[4]

packets = {
    'COMMAND_REJECT'                    :{'Code':0x01,'Pkt':L2CapCommandReject,'minSize':6,'maxSize':23},
    'INFORMATION_REQUEST'               :{'Code':0x0A,'Pkt':L2CapInformationRequest,'minSize':6,'maxSize':6},
    'CONNECTION_PARAM_UPDATE_REQUEST'   :{'Code':0x12,'Pkt':L2CapConnectionParameterUpdateRequest,'minSize':12,'maxSize':12},
    'CONNECTION_PARAM_UPDATE_RESPONSE'  :{'Code':0x13,'Pkt':L2CapConnectionParameterUpdateResponse,'minSize':6,'maxSize':6},
}
opcodeLookup = dict([value['Code'],{'Name':key,'Pkt':value['Pkt'],'minSize':value['minSize'],'maxSize':value['maxSize']}] for key,value in packets.iteritems() if 'Pkt' in value)
pktLookup = dict([value['Pkt'],{'Name':key,'Code':value['Code']}] for key,value in packets.iteritems() if 'Pkt' in value)

