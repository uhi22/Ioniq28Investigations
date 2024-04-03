
# SPI Interpreter

# This script reads an SPI trace, which was recorded with saleae 2 and stored as text file.
# Purpose is to decode the traffic between QCA7005 (QCA7000) and its host processor. The ethernet frames,
# which are contained in the SPI traffic, will be written into a pcap file. Afterwards
# they can be inspected e.g. in WireShark, and further
# converted e.g. with https://github.com/uhi22/pyPLC/blob/master/pcapConverter.py

# Example file: CCM_SPI_powerOn_and_SLAC_until_contractAuth.txt
#
# Format/example:
# Time [s],Packet ID,MOSI,MISO
# 4.742270536000000,0,0xC2,0x00
# 4.742271160000000,0,0x00,0x00
# 4.742272288000000,0,0x00,0x00

# Format2:
#name,type,start_time,"mosi","miso"
#"SPI","enable",35.620134,,
#"SPI","result",35.6201342,0xC2,0x00
#"SPI","result",35.6201348,0x00,0x00
#"SPI","result",35.620136,0x00,0x00



# Precondition: Scapy is installed
# pip install scapy
#import scapy
from scapy.all import raw, wrpcap, Ether

# The list of packets:
allpackets = []


class frameDecoder():
    # Decoder for the QCA7000 SPI.
    # Basic idea: The ethernet frames are announced with a start pattern 0xAAAAAAAA, followed by length and fill pattern.
    # The decoder state machine searches this sequence of patterns, takes the data which comes afterwards as ethernet data,
    # and stores it as network packet, using the scapy library.
    def __init__(self):
        self.state=0
        self.lengthLow = 0
        self.lengthHigh = 0
        self.remainingDataLen = 0
        self.framedata = []
    
    def byteSeen(self, b, timestamp):
        # For each byte in the SPI traffic, this function is called.
        if (self.state==0): # waiting for the start pattern
            if (b==0xAA):
                self.state=1
                return
            else:
                self.state = 0
                return
        if (self.state==1): # waiting for second start pattern byte
            if (b==0xAA):
                self.state=2
                return
            else:
                self.state = 0
                return
        if (self.state==2): # waiting for third start pattern byte
            if (b==0xAA):
                self.state=3
                return
            else:
                self.state = 0
                return
        if (self.state==3): # waiting for fourth start pattern byte
            if (b==0xAA):
                self.state=4 # preamble of 0xAAAAAAAA finished
                return
            else:
                self.state = 0
                return
        if (self.state==4): # waiting for the length information
            self.lengthLow = b
            self.state=5
            return
        if (self.state==5): # waiting for the second part of the length information
            self.lengthHigh = b
            self.state=6
            return
        if (self.state==6): # waiting for the zero fill byte
            if (b==0):
                self.state=7
                return
            else:
                self.state = 0
                return
        if (self.state==7): # waiting for the second zero fill byte
            if (b==0):
                self.state=8 # preamble of 0xAAAAAAAA and length and 0x0000 finished. Ready for data.
                self.remainingDataLen = self.lengthHigh * 256 + self.lengthLow
                print("header seen. Looking for " + str(self.remainingDataLen) + " bytes frame data.")
                self.framedata = []
                return
            else:
                self.state = 0
                return
        if (self.state==8): # receiving data
            if (self.remainingDataLen>0):
                self.framedata.append(b) # add the data byte to the list of data bytes
                self.remainingDataLen-=1 # decrement the number of remaining bytes
                if (self.remainingDataLen==0): # all data received
                    print("frame " + prettyHexMessage(self.framedata))
                    packet = Ether(raw(self.framedata)) # create a scapy packet from the byte list
                    packet.time = timestamp # set the time stamp of the scapy packet with the time stamp of the last byte
                    allpackets.append(packet) # add to the list of packets
                    packet.show() 
                    self.state = 0 # wait for the next start pattern
                return


def twoCharHex(b):
    strHex = "%0.2X" % b
    return strHex


def prettyHexMessage(mybytearray, description=""):
    packetlength = len(mybytearray)
    strHex = ""
    for i in range(0, packetlength):
        strHex = strHex + twoCharHex(mybytearray[i]) + " "
    return description + "(" + str(packetlength) + "bytes) = " + strHex



def readSpiTrace(inputFileName):
    mosiDecoder = frameDecoder()
    misoDecoder = frameDecoder()
    with open(inputFileName) as file:
        for line in file:
            #print(line.strip())
            elementList = line.strip().split(",")
            if (len(elementList)==4):
                strTime = elementList[0]
                try:
                    t = float(strTime)
                except:
                    t = 0.0
                strMosiData = elementList[2]
                mosi = 0
                try:
                    mosi = int(strMosiData, 0) # convert string like "0xAA" into number
                    #print("ok" + hex(x))
                except:
                    # ignore invalid values
                    pass
                mosiDecoder.byteSeen(mosi, t)
                strMisoData = elementList[3]
                miso = 0
                try:
                    miso = int(strMisoData, 0) # convert string like "0xAA" into number
                    #print("ok" + hex(x))
                except:
                    # ignore invalid values
                    pass
                misoDecoder.byteSeen(miso, t)
            if (len(elementList)==5):
                strTime = elementList[2]
                try:
                    t = float(strTime)
                except:
                    t = 0.0
                strMosiData = elementList[3]
                mosi = 0
                try:
                    mosi = int(strMosiData, 0) # convert string like "0xAA" into number
                    #print("ok" + hex(x))
                except:
                    # ignore invalid values
                    pass
                mosiDecoder.byteSeen(mosi, t)
                strMisoData = elementList[4]
                miso = 0
                try:
                    miso = int(strMisoData, 0) # convert string like "0xAA" into number
                    #print("ok" + hex(x))
                except:
                    # ignore invalid values
                    pass
                misoDecoder.byteSeen(miso, t)
                        

strSpiTraceFileName = "spi_ioniq_alpiHYC150_Meitingen_twoSessions_2024-04-03_Ok.csv"
# parse the SPI trace and collect the network packets
readSpiTrace(strSpiTraceFileName)
# write the collected packets into pcap file
wrpcap(strSpiTraceFileName + ".pcap", allpackets)
print("Done. " + strSpiTraceFileName + ".pcap written.")
