/* SPI Flash Readout */

/* Board: Arduino Pro Mini */

#define SOFTSPI_MISO 5
#define SOFTSPI_CS 6
#define SOFTSPI_MOSI 4
#define SOFTSPI_CLK 3

#define READ_BUFFER_LEN 32
uint8_t readbuffer[READ_BUFFER_LEN];
uint32_t address;

#define USE_OUTPUTFORMAT_S19

uint8_t softspi_talk8bit(uint8_t b) {
  int i;
  uint8_t miso=0;
  for (i=0; i<8; i++) {
      /* https://www.tme.eu/Document/90cf95a7114025302d33a68125e207ab/MX25L1606E.pdf says
         input data is latched on rising edge of sclk, and shifted on falling edge. 
         We use mode 3, clock is high while idle. MSB is shifted first. */
      digitalWrite(SOFTSPI_CLK, LOW);
      if (b & 0x80) {
        digitalWrite(SOFTSPI_MOSI, HIGH);
      } else {
        digitalWrite(SOFTSPI_MOSI, LOW);        
      }
      b<<=1;      
      digitalWrite(SOFTSPI_CLK, HIGH);
      miso<<=1;
      if (digitalRead(SOFTSPI_MISO)) miso|=1;      
        
  } 
  return miso;  
}

uint32_t ReadIdentification(void) {
 /* Read the 3 byte device identification for the SPI flash.
    Example: For the device https://www.tme.eu/Document/90cf95a7114025302d33a68125e207ab/MX25L1606E.pdf,
    it returns 0xC22015, which is manufacturer 0xC2, memory type 0x20 and memory density 0x15. */
  int i;
  uint8_t miso=0;
  uint32_t id=0;  
  digitalWrite(SOFTSPI_CS, LOW);
  softspi_talk8bit(0x9F); /* 9F is Read Identification (RDID) */
  miso=softspi_talk8bit(0x00);
  id = miso;
  id<<=8;
  miso=softspi_talk8bit(0x00);
  id |= miso;
  id<<=8;
  miso=softspi_talk8bit(0x00);
  id |= miso;
  digitalWrite(SOFTSPI_CS, HIGH);
  return id;  
 }

void ReadFromAddress(uint32_t address) {
 /* Reads */
  int i;
  uint8_t miso=0;
  uint32_t id=0;
  digitalWrite(SOFTSPI_CS, LOW);
  softspi_talk8bit(0x03); /* 03 is read command */
  softspi_talk8bit(address>>16); /* and 3 bytes address */
  softspi_talk8bit(address>>8);
  softspi_talk8bit(address);
  /* in the same chipselect cycle, read as many bytes as you like */
  for (i=0; i<READ_BUFFER_LEN; i++) {
    readbuffer[i]=softspi_talk8bit(0x00);
  }
  digitalWrite(SOFTSPI_CS, HIGH); 
}

String twoByteHex(uint8_t b) {
  String s;
  s = String(b, HEX);
  if (s.length()==1) s = "0" + s;
  return s;
}

void readAll(void) {
  String sAddr;
  String sData;
  String sAscii;
  String sChecksum;
  uint8_t b, i;
  uint8_t sum;
  //uint32_t maxAddress = 0x10000; /* 64kByte for test */
  uint32_t maxAddress = 2*1024uL*1024uL; /* 2MB full memory size */
  
  while (address<maxAddress) {
    sAddr =  twoByteHex(address>>16)  +   twoByteHex(address>>8) + twoByteHex(address) ;
    ReadFromAddress(address);
    sData = "";
    sAscii = "";
    for (i=0; i<READ_BUFFER_LEN; i++) {
      b=readbuffer[i];
      sData = sData + twoByteHex(b);
      #ifndef USE_OUTPUTFORMAT_S19
        sData = sData + " "; /* spaces between the data for better readability */
      #endif      
      if (b<0x20) b=0x21;
      sAscii = sAscii + (char)b;
    }
    #ifdef USE_OUTPUTFORMAT_S19
      /* print an S19 line to console. This can be recorded e.g. with Putty to a file, to have an S19 file in the end. */
      sum = 0;
      sum+=0x25;
      sum+=address>>16;
      sum+=address>>8;
      sum+=address;
      for (i=0; i<READ_BUFFER_LEN; i++) {
        sum+=readbuffer[i];
      }
      sum ^= 0xFF; /* we need the ones-complement of the sum */
      sChecksum =twoByteHex(sum);
      sAddr = "00" + sAddr; /* extend the 3 byte address to 4 byte address. */
      /* S3 means: 4-byte address. 25 is the number of bytes incl address and checksum */
      Serial.println("S325" + sAddr + sData + sChecksum);      
    #else
      /* print a readable string to the console, consisting of address, data as hex and data as ASCII */
      Serial.println(sAddr + ":" + sData + "  " + sAscii);
    #endif
    address+=READ_BUFFER_LEN;
  }    

  
}

void setup()
{
  int i;
  pinMode(SOFTSPI_CLK, OUTPUT);
  pinMode(SOFTSPI_MOSI, OUTPUT);
  pinMode(SOFTSPI_CS, OUTPUT);
  pinMode(SOFTSPI_MISO, INPUT);

  digitalWrite(SOFTSPI_CS, HIGH);
  digitalWrite(SOFTSPI_CLK, HIGH);
  digitalWrite(SOFTSPI_MOSI, HIGH);
  Serial.begin(230400);
  Serial.println("Started");
  Serial.print("Identification:");
  Serial.println(ReadIdentification(), HEX);
  readAll();
  
  Serial.println("Done");

}


void loop()
{
}  