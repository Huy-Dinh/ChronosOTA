# File that defines calsses and function that are that describes ACIM Commands and event
import sys
from testerScriptCommon import *
class AciDynData:
    ACI_DD_TAGS = {
    'ACI_DD_TAG_INVALID' : 0x00,
    'ACI_DD_TAG_DEVSETT' : 0x01,
    'ACI_DD_TAG_ATTDB' : 0x02,
    'ACI_DD_TAG_REM_ATTRS' : 0x03,
    'ACI_DD_TAG_MRG_LIN' : 0x04,
    'ACI_DD_TAG_CRC' : 0x05,
    'ACI_DD_TAG_COMPLETE' : 0x06,
    }
    ACI_DD_TAG = dict([value,key] for key,value in ACI_DD_TAGS.iteritems())

    def __init__(self, testIF):
        self.raw_data = []
        self.seqs = []
        self.testIF = testIF

    def __cmp__(self, other):
        if self.raw_data == other.raw_data and self.seqs == other.seqs:
            self.testIF.dut.LogWrite("DUT: __cmp__ match")
            return 0
        else:
            self.testIF.dut.LogWrite("DUT: __cmp__ *no* match")
            return 1

    def feed(self, data):
        self.raw_data = self.raw_data + data[1:]
        self.seqs.append([len(data) - 1, data[0]])
        self.testIF.dut.LogWrite("DUT: %d bytes of dynamic data fed,  RDD Sequence Number: %d" % (len(data) - 1, data[0]))

    def parse(self):
        self.testIF.dut.LogWrite("DUT: Parsing dynamic data:")
        idx = 0
        while idx < len(self.raw_data):
            self.testIF.dut.LogWrite("DUT: idx: %d len: %d" % (idx, len(self.raw_data)) )
            tag= self.raw_data[idx] >> 2
            tag_count = self.raw_data[idx + 1] | ((self.raw_data[idx] & 0x3) << 8)
            ccount = 0
            idx = idx + 2
            self.testIF.dut.LogWrite("DUT: Tag Found: %s (tag count: %d)" % (AciDynData.ACI_DD_TAG[tag], tag_count))
            if(AciDynData.ACI_DD_TAG[tag] == 'ACI_DD_TAG_INVALID'):
                self.testIF.dut.LogWrite("DUT: Invalid tag: %s" % AciDynData.ACI_DD_TAG[tag])
                return False
            elif(AciDynData.ACI_DD_TAG[tag] == 'ACI_DD_TAG_DEVSETT'):
                self.testIF.dut.LogWrite("DUT: output_power: %d (0x%02X)" % (self.raw_data[idx + 0], self.raw_data[idx + 0]))
                self.testIF.dut.LogWrite("DUT: name_short_len: %d (0x%02X)" % (self.raw_data[idx + 1], self.raw_data[idx + 1]))
                idx = idx + 2
            elif(AciDynData.ACI_DD_TAG[tag] == "ACI_DD_TAG_ATTDB"):
                while(ccount < tag_count and idx < len(self.raw_data)):
                    handle = self.raw_data[idx + 0] << 8 | self.raw_data[idx + 1]
                    vlen = self.raw_data[idx + 2]
                    self.testIF.dut.LogWrite("DUT: ATTDB entry: handle=0x%04X vlen=%d" % (handle, vlen))
                    idx = idx + 3
                    value = self.raw_data[idx : idx + vlen]
                    self.testIF.dut.LogWrite("DUT: ATTDB entry value: %s" % (self.testIF.dut.GetHexString(value)))
                    idx = idx + vlen
                    ccount = ccount + 1
            elif(AciDynData.ACI_DD_TAG[tag] == "ACI_DD_TAG_REM_ATTRS"):
                while(ccount < tag_count and idx < len(self.raw_data)):
                    attr_idx = self.raw_data[idx + 0]
                    handle_value = self.raw_data[idx + 1] << 8 | self.raw_data[idx + 2]
                    handle_cccd = self.raw_data[idx + 3] << 8 | self.raw_data[idx + 4]
                    state = self.raw_data[idx + 5]
                    self.testIF.dut.LogWrite("DUT: Rem Attr entry: attr_idx=%d handle_value=0x%04X handle_cccd=0x%04X state=%02X" % (attr_idx, handle_value, handle_cccd, state))
                    idx = idx + 6
                    ccount = ccount + 1
            elif(AciDynData.ACI_DD_TAG[tag] == "ACI_DD_TAG_MRG_LIN"):
                self.testIF.dut.LogWrite("DUT: MRG linear entry value: %s" % (self.testIF.dut.GetHexString(self.raw_data[idx : idx + tag_count])))
                idx = idx + tag_count
            elif(AciDynData.ACI_DD_TAG[tag] == "ACI_DD_TAG_CRC"):
                crc_16_ccitt = self.raw_data[idx + 0] << 8 | self.raw_data[idx + 1]
                self.testIF.dut.LogWrite("DUT: CRC: crc_16_ccitt=0x%04X" % (crc_16_ccitt))
                idx = idx + 2
            else:
                self.testIF.dut.LogWrite("DUT: Invalid tag: %s" % AciDynData.ACI_DD_TAG[tag])
                return False
        return True
    
    def waitForCR(self, opcode):
        retval = self.testIF.dut.WaitFor(self.testIF.dut.ANY_PACKET, T=2, NO_PRINT = 1)
        if isinstance(retval, AciCommandResponseEvent):
            self.testIF.dut.LogWrite("DUT: Received ACI_EVT_CMD_RSP, EventCode: 0x%02X, Length: %d, Content: %s" % (retval.EventCode, retval.Length, self.testIF.dut.GetHexString(retval.Content)))            
            if retval.CommandCode == opcode:
                self.testIF.dut.LogWrite("DUT: Correct Command OpCode: 0x%02X" % retval.CommandCode)
                self.testIF.dut.AssertTrue(True)
                status = retval.Status
            else:
                self.testIF.dut.LogWrite("DUT: Wrong Command Code")
                self.testIF.dut.AssertTrue(False)
                return self.testIF.aciCmds.UNKNOWN
            if status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_CONTINUE:
                self.testIF.dut.LogWrite("DUT: Status: ACI_STATUS_TRANSACTION_CONTINUE")
                self.rx_packet = retval
                return status
            elif status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_COMPLETE:
                self.testIF.dut.LogWrite("DUT: Status: ACI_STATUS_TRANSACTION_COMPLETE")
                self.rx_packet = retval
                return status
            else:
                self.testIF.dut.LogWrite("DUT: Status: ERROR")
                self.testIF.dut.AssertTrue(False) 
                return status
        else:
            self.testIF.dut.LogWrite("DUT: Failed to receive a Command Response")
            self.testIF.dut.AssertTrue(False, reason = "No Command Response for 2 seconds")
            return self.testIF.aciCmds.UNKNOWN

    def read(self):
        self.testIF.dut.LogWrite("DUT: Reading dynamic data...")
        while True:
            self.testIF.dut.LogWrite("DUT: Sending READ_DYNAMIC_DATA ACI command")
            self.testIF.aciCmds.ReadDynamicData()
            status = self.waitForCR(self.testIF.aciCmds.ACI_CMD_READ_DYNAMIC_DATA)
            if status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_CONTINUE:
                self.feed(self.rx_packet.CommandRespParam)
            elif status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_COMPLETE:
                self.feed(self.rx_packet.CommandRespParam)
                self.testIF.dut.AssertTrue(True) 
                return True
            else:
                return False

    def write(self):
        self.testIF.dut.LogWrite("DUT: Writing dynamic data...")
        count = 0
        for i in range(len(self.seqs)):
            self.testIF.dut.LogWrite("DUT: Sequence: seq_len=%d seq_no=%d seq: %s" % (self.seqs[i][0], self.seqs[i][1], self.testIF.dut.GetHexString(self.raw_data[count : count + self.seqs[i][0]])))
            self.testIF.dut.LogWrite("DUT: Sending WRITE_DYNAMIC_DATA ACI command")
            self.testIF.aciCmds.WriteDynamicData(self.seqs[i][1], self.raw_data[count : count + self.seqs[i][0]])
            status = self.waitForCR(self.testIF.aciCmds.ACI_CMD_WRITE_DYNAMIC_DATA)
            if status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_CONTINUE:
                self.testIF.dut.AssertTrue(True) 
            elif status == self.testIF.aciCmds.ACI_STATUS_TRANSACTION_COMPLETE:
                self.testIF.dut.AssertTrue(i == len(self.seqs) - 1, reason="COMPLETE received before sending all dyndata packets") 
            else:
                self.testIF.dut.AssertTrue(False) 
                return False
            count = count + self.seqs[i][0]
        self.testIF.dut.LogWrite("DUT: Dynamic Data written.")
        return True

