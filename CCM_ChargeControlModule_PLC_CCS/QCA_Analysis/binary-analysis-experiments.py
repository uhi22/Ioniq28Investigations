
import os
import sys
import zlib # https://docs.python.org/3/library/zlib.html
import binascii


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
            x = datablocks[offset+0]
            x *= 256
            x += datablocks[offset+1]
            x *= 256
            x += datablocks[offset+2]
            x *= 256
            x += datablocks[offset+3]
            number3 =  datablocks[offset+4]
            if ((x == 0x01000100) and (number3 == 3)):
                blocktype = datablocks[offset+5]
                strBlockType = "unkown block type " + hex(blocktype)
                if (blocktype == 0):
                    strBlockType = "0=table"
                elif (blocktype == 0x40):
                    strBlockType = "0x40=table"
                elif (blocktype == 0x80):
                    strBlockType = "0x80=compressedApplication"
                    offsetOfCompressedApplication = offset
                    compressedSize = self.getUInt32LittleEndian(datablocks, offset+0xe8)
                    strBlockType += " with compressed size " + str(compressedSize)
                print("Offset " + hex(offset) + " is the beginning of a header. Block type " + strBlockType)
            offset += 1
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
            
    def compareBinaries(self):
        NECESSARY_NUMBER_OF_IDENTICAL_BYTES = 4
        if (self.data1OffsetOfCompressedApplication < 0):
            print("cannot compare, because application 1 not found")
            return
        if (self.data2OffsetOfCompressedApplication < 0):
            print("cannot compare, because application 2 not found")
            return
        numberOfHits = 0
        index1 = self.data1OffsetOfCompressedApplication + 0xf0 # offset where the compressed data starts
        
        blEndOfX1 = 0
        while (blEndOfX1 == 0): # loop through the left side
            blEndOfX2 = 0
            index2 = self.data2OffsetOfCompressedApplication + 0xf0 # offset where the compressed data starts
            while (blEndOfX2 == 0): # loop through the complete right side
                loopIndex = 0
                isIdentical = 1
                strIdenticalData = "at left: " + hex(index1) + ", right: " + hex(index2) + " : "
                while (isIdentical == 1) and (blEndOfX2 == 0): # loop while we are in an identical part
                    x1 = self.data1[index1 + loopIndex]
                    if (index2 + loopIndex < len(self.data2)):
                        x2 = self.data2[index2 + loopIndex]
                    else:
                        x2 = 0
                        blEndOfX2 = 1
                    if (x1 == x2):
                        strIdenticalData += " " + hex(x1)
                        loopIndex += 1
                    else:
                        isIdentical = 0
                        if (loopIndex>=NECESSARY_NUMBER_OF_IDENTICAL_BYTES):
                            print("this was a relevant part " + strIdenticalData)
                            numberOfHits += 1
                        index2 += 1 # go to the next candidate on the right side.
            index1 += 1 # go to the next candidate on the left side.
            deltaAtLeft = index1 - (self.data1OffsetOfCompressedApplication + 0xf0)
            if ((deltaAtLeft % 100)==0):
                print("checking at delta " + str(deltaAtLeft))
            #if (index1>self.data1OffsetOfCompressedApplication + 0xf0 + 100000):
            #    blEndOfX1 = 1

    def tryToUncompressAsZLib(self):
        # https://docs.python.org/3/library/zlib.html
        # with negative wbits to indicate a raw headerless stream
        myStream = self.data1[self.data1OffsetOfCompressedApplication + 0xf0: self.data1OffsetOfCompressedApplication + 0xf0 + self.data1CompressedSize]
        print("len of compressed data: " + str(len(myStream)))
        decompressed_data = zlib.decompress(myStream, wbits = -8)
        print(binascii.hexlify(decompressed_data[0:100]))

        
    # read the file and store the data in "data"
    def __init__(self):
        filename1 = "CCM_FlashDump_SpiFlash_Ioniq_compressed_part.bin"
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
        self.showHeader(self.data1, self.data1OffsetOfCompressedApplication)

        filename2 = "MAC-7420-v1.3.1-00-CSnvm.bin"
        if not os.access(filename2, os.F_OK):
            print_error('Input file ({0}) does not exist'.format(filename2))
            exit(0)
        f = open(filename2, "rb")
        self.data2 = f.read()
        f.close()
        print("data2 from " + filename2)
        self.filesize2 = len(self.data2)
        print("filesize2: " + str(self.filesize2))
        (self.data2OffsetOfCompressedApplication, self.data2CompressedSize) = self.searchHeader(self.data2)
        self.showHeader(self.data2, self.data2OffsetOfCompressedApplication)
        

analyzer = binaryAnalyzer()
#analyzer.showStatistics()
#analyzer.compareBinaries()
analyzer.tryToUncompressAsZLib()

