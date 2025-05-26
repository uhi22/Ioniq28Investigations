
import os
import sys



class binaryAnalyzer():
    # returns an uint32, based on the four input bytes. Low byte first.
    def getUInt32LittleEndian(self, position):
        x = self.data[position+3]
        x *= 256
        x += self.data[position+2]
        x *= 256
        x += self.data[position+1]
        x *= 256
        x += self.data[position+0]
        return x
        
    def showHeader(self):
        x = self.data[0]
        x *= 256
        x += self.data[1]
        x *= 256
        x += self.data[2]
        x *= 256
        x += self.data[3]
        print(hex(x))
        if (x == 0x01000100):
            print("This is the beginning of the header.")
        else:
            print("Error: Did not see the header 01 00 01 00.")
        x = self.data[4]
        x *= 256
        x += self.data[5]
        print(hex(x))
        if (x == 0x0380):
            print("Indication for compressed application.")
        else:
            print("Error: Did not see the indication for compressed application 03 80")
        self.compressedSize = self.getUInt32LittleEndian(0xe8)
        print("compressedSize " + hex(self.compressedSize) + " " + str(self.compressedSize))
        self.uncompressedSize = self.getUInt32LittleEndian(0xec)
        print("uncompressedSize " + hex(self.uncompressedSize) + " " + str(self.uncompressedSize))
        self.startOfCompressedData = 0xf0 # offset where the compressed data starts
        self.positionOfLastData = self.startOfCompressedData + self.compressedSize - 1
        print("last data at " + str(self.positionOfLastData))
        if (self.positionOfLastData == self.blocksize - 1):
            print("Size information is consistent.")
        else:
            print("Error: positionOfLastData does not match block size.")

    # calculated statistics over the data
    def showStatistics(self):
        histogramdata =  [0] * 256 # list with 256 elements, all with value 0.
        for i in range(self.startOfCompressedData, self.positionOfLastData+1):
            v = self.data[i]
            histogramdata[v]+=1
        for i in range(0, 256):
            print(str(i) + " " + str(histogramdata[i]))

    # read the file and store the data in "data"
    def __init__(self):
        filename = "CCM_FlashDump_SpiFlash_Ioniq_compressed_part.bin"
        if not os.access(filename, os.F_OK):
            print_error('Input file ({0}) does not exist'.format(filename))
            exit(0)
        f = open(filename, "rb")
        self.data = f.read()
        f.close()
        self.blocksize = len(self.data)
        print("block size: " + str(self.blocksize))

analyzer = binaryAnalyzer()
analyzer.showHeader()
analyzer.showStatistics()


