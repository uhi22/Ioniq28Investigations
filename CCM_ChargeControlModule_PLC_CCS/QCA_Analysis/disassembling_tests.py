# disassembling_tests.py
from capstone import *


def twoCharHex(b):
    strHex = "%0.2X" % b
    return strHex

def showAsHex(mybytearray, description=""):
    packetlength = len(mybytearray)
    strHex = ""
    for i in range(0, packetlength):
        strHex = strHex + twoCharHex(mybytearray[i]) + " "
    print(description + "(" + str(packetlength) + "bytes) = " + strHex)

def prettyHexMessage(mybytearray, description=""):
    packetlength = len(mybytearray)
    strHex = ""
    for i in range(0, packetlength):
        strHex = strHex + twoCharHex(mybytearray[i]) + " "
    return description + "(" + str(packetlength) + "bytes) = " + strHex

#CODE = b"\xda\xba\x9b\x3b\xca\x54\x5e\x46"


# The "return" aka MOV PC, LR
CODE = b"\x0E\xF0\xA0\xE1"
# same as Thumb code
CODE = b"\xF7\x46"


f = open("CCM_FlashDump_SpiFlash_2MB_Ioniq_00_33_79.bin", mode="rb")
f.seek(0x63d40)
#CODE = f.read(8)
f.close()
print("code: " + prettyHexMessage(CODE))

md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
#md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
for i in md.disasm(CODE, 0x1000):
    print("                     " + prettyHexMessage(i.bytes))
    print("0x%x:\t%s\t%s" %(i.address, i.mnemonic, i.op_str))