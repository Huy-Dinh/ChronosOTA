#! /usr/bin/python
from modules.common import DefaultPktFunctions, Utilities
# import Exceptions
from modules.common import PacketLengthError

from protocol.Smp import SmpPkt
from protocol.Att import AttPkt
from protocol.L2CapSignPkt import L2CapSignalingPkt

packets = {
    'ATT_PKT'   :{'Code':0x0004,'Pkt':AttPkt},
    'L2CAP_PKT' :{'Code':0x0005,'Pkt':L2CapSignalingPkt},
    'SMP_PKT'   :{'Code':0x0006,'Pkt':SmpPkt},
}
opcodeLookup = dict([value['Code'],{'Name':key,'Pkt':value['Pkt']}] for key,value in packets.iteritems() if 'Pkt' in value)
pktLookup = dict([value['Pkt'],{'Name':key,'Code':value['Code']}] for key,value in packets.iteritems() if 'Pkt' in value)

class L2CapPkt(DefaultPktFunctions):
    EventCode = 0x97
    def __new__(clr, *args, **argv):
        if ('packet' in argv and clr == L2CapPkt):
            # Check if the Code is in the valid codes
            packet  = [int(el) for el in argv['packet']]
            length  = packet[0] | (packet[1] << 8)
            code    = packet[2] | (packet[3] << 8)
            data    = packet[4:4+length]
            if code in opcodeLookup:
                # Fetching the packet type to generate
                packetType = opcodeLookup[code]['Pkt']
                # Generate and return the correct packet type
                retval = packetType(packet=data)
                retval.L2capPkt = super(L2CapPkt, GeneralL2CapPacket).__new__(GeneralL2CapPacket)
                return retval
            # If the code were not in the "known" packet list, return a General L2Cap Packet
            return super(L2CapPkt, GeneralL2CapPacket).__new__(GeneralL2CapPacket)
        
        # The packet type to construct is known, no need to find the Packet Type to construct
        return super(L2CapPkt,clr).__new__(clr)
        
    def __init__(self, *args, **argv):
        self.Content = []
        # If 'packet' is in the argv, we know it has to be parsed (all classes need to implement create, build and parse)
        if 'packet' in argv:
            packet = argv['packet']
            # Putting the packet inside the Content of the Class
            self.Content = [int(el) for el in packet]
            # Defining the code of the Class
            self.Length  = packet[0] | (packet[1] << 8)
            self.Code    = packet[2] | (packet[3] << 8)
            self.Data    = packet[4:4+self.Length]
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

class GeneralL2CapPacket(L2CapPkt):
    pass
