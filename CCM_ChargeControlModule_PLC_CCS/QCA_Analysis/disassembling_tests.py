# disassembling_tests.py
from capstone import *
import os
import sys
import binascii


strBinFileName = "CCM_FlashDump_SpiFlash_2MB_Ioniq_00_33_79.bin"
adEntryPoint = 0x0
adBinaryBase = 0x0
sizeOfDisassemblingChunk = 256
nNumberOfJumps = 0


class binaryAnalyzer():
    # returns an uint32, based on the four input bytes. Low byte first.
    def getUInt32LittleEndian(self, datablock, position):
        x = datablock[position+3]
        x *= 256
        x += datablock[position+2]
        x *= 256
        x += datablock[position+1]
        x *= 256
        x += datablock[position+0]
        return x
    
    def searchHeader(self, datablocks):
        # searches for the header of the compressed application in a file which may contain multiple blocks.
        offsetOfCompressedApplication = -1 # mark as invalid
        compressedSize = -1
        offset = 0
        while (offset<len(datablocks)-8):
            x = self.getUInt32LittleEndian(datablocks, offset)
            blocktype = self.getUInt32LittleEndian(datablocks, offset+4)
            if ((x == 0x00010001)):
                addressOfSubHeader = self.getUInt32LittleEndian(datablocks, offset+0x08)
                addressOfNextBlock = self.getUInt32LittleEndian(datablocks, offset+0x1C)
                addressOfPrevBlock = self.getUInt32LittleEndian(datablocks, offset+0x20)
                magic1234 = self.getUInt32LittleEndian(datablocks, offset+0x68)
                blockDescriptionString = ""
                for i in range(0, 20):
                    blockDescriptionString += chr(datablocks[offset-0x160+i])
                strBlockType = "unkown block type " + hex(blocktype)
                if (blocktype == 0x0000):
                    strBlockType = "0x0000=identification"
                elif (blocktype == 0x0003):
                    strBlockType = "0x0003=table"
                elif (blocktype == 0x4003):
                    strBlockType = "0x4003=table"
                elif (blocktype == 0x8003):
                    strBlockType = "0x8003=compressedApplication"
                    offsetOfCompressedApplication = offset
                    compressedSize = self.getUInt32LittleEndian(datablocks, offset+0xe8)
                    strBlockType += " with compressed size " + str(compressedSize)
                
                print("Offset " + hex(offset) + " is the beginning of a header.")
                print("  Block type " + strBlockType + " " + blockDescriptionString)
                print("  magic " + hex(magic1234))
                print("  addressOfNextBlock " + hex(addressOfNextBlock))
                print("  addressOfPrevBlock " + hex(addressOfPrevBlock))
                
                if (addressOfSubHeader == (offset+0x60) & 0xffff):
                    print("  subheader address match")
                else:
                    print("  addressOfSubHeader " + hex(addressOfSubHeader))
                if (magic1234 == 0x1234abcd) or (addressOfSubHeader == (offset+0x60) & 0xffff):
                    print("  Qualified block header")
            offset += 4
        return (offsetOfCompressedApplication, compressedSize)
            
    def showHeader(self, datablock, offset):
        x = datablock[offset+0]
        x *= 256
        x += datablock[offset+1]
        x *= 256
        x += datablock[offset+2]
        x *= 256
        x += datablock[offset+3]
        print(hex(x))
        if (x == 0x01000100):
            print("This is the beginning of the header.")
        else:
            print("Error: Did not see the header 01 00 01 00.")
        x = datablock[offset+4]
        x *= 256
        x += datablock[offset+5]
        print(hex(x))
        if (x == 0x0380):
            print("Indication for compressed application.")
        else:
            print("Error: Did not see the indication for compressed application 03 80")
        compressedSize = self.getUInt32LittleEndian(datablock, offset+0xe8)
        print("compressedSize " + hex(compressedSize) + " " + str(compressedSize))
        uncompressedSize = self.getUInt32LittleEndian(datablock, offset+0xec)
        print("uncompressedSize " + hex(uncompressedSize) + " " + str(uncompressedSize))
        compressionRatio = compressedSize / uncompressedSize
        print("compression ratio " + str(compressionRatio*100) + "%")
        self.startOfCompressedData = offset+0xf0 # offset where the compressed data starts
        self.positionOfLastData = self.startOfCompressedData + compressedSize - 1
        print("last data at " + str(self.positionOfLastData))
        #if (self.positionOfLastData == self.blocksize - 1):
        #    print("Size information is consistent.")
        #else:
        #    print("Error: positionOfLastData does not match block size.")

    # calculated statistics over the data
    def showStatistics(self):
        histogramdata =  [0] * 256 # list with 256 elements, all with value 0.
        for i in range(self.startOfCompressedData, self.positionOfLastData+1):
            v = self.data2[i]
            histogramdata[v]+=1
        for i in range(0, 256):
            print(str(i) + " " + str(histogramdata[i]))
        
    # read the file and store the data in "data"
    def __init__(self):
        filename1 = strBinFileName
        if not os.access(filename1, os.F_OK):
            print_error('Input file ({0}) does not exist'.format(filename1))
            exit(0)
        f = open(filename1, "rb")
        self.data1 = f.read()
        f.close()
        print("data1 from " + filename1)
        self.filesize1 = len(self.data1)
        print("filesize1: " + str(self.filesize1))
        (self.data1OffsetOfCompressedApplication, self.data1CompressedSize) = self.searchHeader(self.data1)
        #self.showHeader(self.data1, self.data1OffsetOfCompressedApplication)

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

def explanation(mnemonic):
    s = ""
    if (mnemonic == "mcr"):
        s = "Move to Coprocessor from ARM core register"
    return s


#CODE = b"\xda\xba\x9b\x3b\xca\x54\x5e\x46"


# The "return" aka MOV PC, LR
#CODE = b"\x0E\xF0\xA0\xE1"
# same as Thumb code
#CODE = b"\xF7\x46"



def toggleInstructionSet(instructionMode):
    # change the instruction set. This is needed to handle instructions like BLX.
    # https://developer.arm.com/documentation/dui0379/e/arm-and-thumb-instructions/blx?lang=en
    # BLX label always changes the instruction set. It changes a processor in ARM state to Thumb state, or a processor in Thumb state to ARM state.
    if (instructionMode == CS_MODE_THUMB):
        print("changing to ARM")
        return CS_MODE_ARM
    else:
        print("changing to THUMB")
        return CS_MODE_THUMB

def showDisassemblyAt(adr, instructionMode):
    global nNumberOfJumps
    nNumberOfJumps += 1
    print("Number of jumps: " +  str(nNumberOfJumps))
    if (nNumberOfJumps>7):
        print("stopping analysis")
        return
    codeForDisassembling = binaryCode[adr-adBinaryBase : adr-adBinaryBase+sizeOfDisassemblingChunk]
    md = Cs(CS_ARCH_ARM, instructionMode)
    for i in md.disasm(codeForDisassembling, adr):
        s = ""
        for b in i.bytes:
            s = s + twoCharHex(b)
        print("0x%x:\t%s\t%s\t%s\t%s" %(i.address, s, i.mnemonic, i.op_str, explanation(i.mnemonic)))
        if (i.mnemonic=="b"):
            if (i.op_str[0]=="#"):
                adrBranchTarget = int(i.op_str[1:], 16)
                print("This is a branch to " + hex(adrBranchTarget))
                showDisassemblyAt(adrBranchTarget, instructionMode)
                break
            else:
                print("Error: This is no immediate branch target. Not yet implemented.")
        elif (i.mnemonic=="beq"):
            if (i.op_str[0]=="#"):
                if (i.address == 0x2090f0):
                    print("nothing special, ignoring jump.")
                else:
                    adrBranchTarget = int(i.op_str[1:], 16)
                    print("This is a branch to " + hex(adrBranchTarget))
                    showDisassemblyAt(adrBranchTarget, instructionMode)
                    break
            else:
                print("Error: This is no immediate branch target. Not yet implemented.")        
        elif (i.mnemonic=="blx"):
            if (i.op_str[0]=="#"):
                adrBranchTarget = int(i.op_str[1:], 16)
                print("This is a subroutine call to " + hex(adrBranchTarget))
                showDisassemblyAt(adrBranchTarget, toggleInstructionSet(instructionMode))
            else:
                print("Error: Wrong target address for blx. Not yet implemented.")
        elif (i.mnemonic=="bx"):
            if (i.op_str=="lr"):
                print("Returning from subroutine.")
                break
            else:
                print("Error: Wrong target address for bx. Not yet implemented.")
        elif (i.mnemonic=="pop"):
            print("pop with " + i.op_str[-3:])
            if (i.op_str[-3:]=="pc}"):
                print("This is a return")
                break



fileHandle = open(strBinFileName, mode="rb")
binaryCode = fileHandle.read()
fileHandle.close()


#showDisassemblyAt(adEntryPoint, CS_MODE_THUMB)
            
            
print("-------------------playground--------------------")

adrPlayground = 0x0440

CODE = binaryCode[adrPlayground-adBinaryBase : adrPlayground-adBinaryBase+200]
print("code: " + prettyHexMessage(CODE))

#md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
for i in md.disasm(CODE, adrPlayground):
    # print("                     " + prettyHexMessage(i.bytes))
    s = ""
    for b in i.bytes:
        s = s + twoCharHex(b)
    print("0x%x:\t%s\t%s\t%s\t%s" %(i.address, s, i.mnemonic, i.op_str, explanation(i.mnemonic)))


print("-------------------binaryAnalyzer--------------------")
analyzer = binaryAnalyzer()