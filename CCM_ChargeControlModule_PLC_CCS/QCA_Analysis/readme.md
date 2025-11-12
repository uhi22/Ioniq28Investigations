
# Analysis of the QCA

# Approach 1: check the firmware

Firmware is available as dump of the SPI flash, and also as official firmware images of the homeplug devices.

## Installation of the Capstone disassembler

https://www.capstone-engine.org/documentation.html

pip install capstone-windows

## Which instruction set?

The data sheet of the QCA7000 says "Integrated ARM CPU" and "ARM926". The ARM926 supports two instruction sets, ARM and Thumb.

Function call: BL, "branch and link". The link register is R14.
Return: MOV PC, LR
In the ARM instruction set: https://iitd-plos.github.io/col718/ref/arm-instructionset.pdf
  condition 1110 = always
  00
  0 immediate: register
  1101 = MOV
  0
  0000 first operand don't care
  1111 destination = r15 = PC
  00000000 1110 second operand = r14 = LR
  Result: 1110 0001 1010 0000 1111 0000 0000 1110 = E1 A0 F0 0E
  capstone wants this in the opposite order: CODE = b"\x0E\xF0\xA0\xE1"

In the Thumb instruction set:
  (https://developer.arm.com/documentation/ddi0419/c/Application-Level-Architecture/Thumb-Instruction-Details/Alphabetical-list-of-ARMv6-M-Thumb-instructions/MOV--register-?lang=en)
  0100 0110 1  1110   111
  Result: 0100 0110 1111 0111 = 46 F7
  capstone wants this in the opposite order: CODE = b"\xF7\x46"

Register usage: https://developer.arm.com/documentation/dui0056/d/using-the-procedure-call-standard/register-roles-and-names/register-roles?lang=en
r13 stack pointer
r14 link register
r15 program counter

## Memory layout?

0x3FA8: "CheckFirmwareIntegrityAndBackupIfNeeded: Primary and Alternate Firmware has invalid Signature!"

0x1'0000 to 0x6'3d47 program block
          real code start 0x1'8ce0

0xe'0000 to 0xe'7fff info and short program?


0x14'0000 TOR-SW-BUILD02 ... buildbot ...  QCA7000 MAC SW v1.1.0 Rev:04 CS-RC2 ...
          FW-QCA7420-1.1.0.730-04-CS-20140815:101156-buildbot:TOR-SW-BUILD02-1-1.2
          to 0x19'3d47
          

## other investigations?

https://www.zibri.org/2009/03/powerline-ethernet-fun-and-secrets.html
lists a lot of firmware versions of the old intellon 6300 including management software.

## binwalk firmware analysis tool

https://github.com/ReFirmLabs/binwalk


## Firmware packages?

e.g. https://www.tp-link.com/de/support/download/tl-pa4010-kit/v2/#Firmware

Hint regarding Third-Party-Firmware like DD-WRT, but this is only for routers.
https://wiki.dd-wrt.com/wiki/index.php/Supported_Devices does not list qca7000 or ar7420 devices.
There is a combined router/homeplug device, https://openwrt.org/toh/tp-link/tl-wpa8630p_v2, but they say "the rest of the partitions (including radio calibration data and PLC firmware) are not touched."

How does the official firmware look like? e.g. TL-PA4010_KIT(EU)_V2_160622_1477643921895p.zip
contains a 400kB MAC-7420-v1.3.1-00-CS.nvm and a 10kB QCA7420-WallAdapter-EN50561-1_622.pib.

The .nvm is a binary file, which looks quite similar than the QCA content. Some identification in the beginning.
Long tables.
Real code starts around 0x85A0 and goes until 0x6'2500. No fill pattern afterwards.

The "startpattern" which the .nvm has at 0x85A0, is in the QCA at 0x1'8ce0 and 0x14'8ce0. 15 bytes are identical: 00 67 80 2d d4 0b dc 7c d8 ce 8d 21 34 35 b3.

At "startpattern-8", at 0x8598 we find the size of the compressed data (0x00059f62).
Same situation in the QCA:
<size> + <startaddress> = <endaddress>
4'b068+14'8ce0=19'3d48
We find the size before the startpattern, at 14'8cd8.
The calculated end address matches the address, where the border between filled data and 0xff fillpattern is.

At startpattern-4 there is an other size information.
It may be the uncompressed size.
- QCA7000: 0x077134=487732 uncompr, 0x04b068=307304 compressed. Ratio 63.0%.
- AR7420: 0x08FC40=588864 uncompr, 0x59f62=368482 compressed. Ratio 62.6%.

At startpattern - 0x78 there is an other size information, which is 0x10 more than the compressedSize.

At startpattern - 0x94 seems to be a CRC32.

- 0xE0 there is an other size information, which is 0x92 or 0x90 more than the compressedSize.

Assumption: A "block" starts with the blockStartToken 01 00 01 00 03.
The byte afterwards specifies the type of block.
- 0x00: table
- 0x40: table
- 0x80: compressed application.

The AR7420 contains 7 blockStartTokens.
The QCA7000 contains 15 blockStartTokens.

blockStartToken + 0x0C: 0x00208400
blockStartToken + 0x18: 0x00208744
These are the same for AR7420 and QCA7000.

Extracted compressed part incl blockStartToken and header informations, for further investigations: CCM_FlashDump_SpiFlash_Ioniq_compressed_part.bin


## Conclusion 1: The firmware images (also on the SPI flash) are "packed".

They do not contain ARM instruction. Seems that the bootloader "unpacks" them into the RAM to get the real executable code.

We have a compression ratio of ~63%. Which compression algorithms are likely?

Google "compression algorithms microcontrollers" says LZ4, SMASH, LZ77. Further candidates: LZSS, LZW, LZ0, Snappy, deflate, ...

### Trial 1: ZLIB

References:
* https://de.wikipedia.org/wiki/Datenkompression : "1995 zlib, freie Standardbibliothek für Deflate"
* https://de.wikipedia.org/wiki/Zlib
* https://zlib.net/
* https://docs.python.org/3/library/zlib.html
* https://stackabuse.com/python-zlib-library-tutorial/

Results:

```
decompressed_data = zlib.decompress(myStream, wbits = -8)
zlib.error: Error -3 while decompressing data: invalid stored block lengths
```
Same result with all wbit = -8 to -15.

### Not-compressed parts of the Ioniq binary

We find 426 occurences of the typical return from subroutine (with included switch of the instruction set from ARM to THUMB) `1EFF2FE1        bx      lr`.

At 0x440 there is ARM code.



# Approach 2: Use the JTAG


https://sergioprado.blog/2020-02-20-extracting-firmware-from-devices-using-jtag/#:~:text=Through%20a%20feature%20called%20Boundary,memory%2C%20flash%2C%20etc).

## JTAG USB adapter

https://blog.adafruit.com/2019/11/20/open-source-ftdi-ft2232-jtag-and-uart-adapter-ftdi-usb-mcuoneclipse/

## JTAG theory

The JTAG state machine: https://www.xjtag.com/about-jtag/jtag-a-technical-overview/

Debug sequence at startup: https://www2.lauterbach.com/pdf/app_arm_jtag.pdf page 16 "Reset Considerations"

Diving into JTAG (but for newer ARM) https://piolabs.com/blog/engineering/diving-into-arm-debug-access-port.html

ARM926 https://developer.arm.com/documentation/ddi0198/e/signal-descriptions/jtag-signals
ARM926 Reference manual: https://developer.arm.com/documentation/ddi0198/e/
and https://ww1.microchip.com/downloads/en/DeviceDoc/ARM_926EJS_TRM.pdf

ARM9EJ-S Technical Reference Manual https://www.google.de/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwip752jxeqGAxWk3QIHHffGA88QFnoECBQQAQ&url=https%3A%2F%2Fdocumentation-service.arm.com%2Fstatic%2F5e8e476f88295d1e18d3aecb%3Ftoken%3D&usg=AOvVaw0_nYlc2soQ_Z6WIbWdBBg9&opi=89978449
and https://developer.arm.com/documentation/ddi0222/b/

### DDI0222.pdf, Annex B

- two scan chains
- for performing memory access, scan chain (aka scan path) 1 is used.
- The instruction register is four bits in length.
- Instruction is set via JTAG TAP, states SHIFT-IR and then UPDATE-IR
- Using instruction SCAN_N (0b0010) and SHIFT-DR and UPDATE-DR, select the scan path.
- Scan chain 1 has 67 bits.
- The 67 bits consist of INSTR[32], SYSPEED, WPTANDBKPT, unused[1] and RDATA/WDATA[32]
- Bit 0 of RDATA/WDATA is the first which is shifted out.
- INSTR has the same meaning as instruction bus, so this takes e.g. ARM instruction.
- RDATA/WDATA has the same meaning as the data read/write bus between core and memory.
- The debug state is entered by setting DBGRQ in the "debug control register" (6 bits wide).
- The "debug control register" is register 0 of the EmbeddedICE-RT.
- The registers of the EmbeddedICE-RT can be written and read via the scan chain 2.
- This access contains 32 bit data, 5 bit address and a R/W bit.

Procedure draft:
- enter debug state, by setting ScanChain2.EmbeddedICE.DebugControlRegister.DBGRQ = 1
- core does not execute instructions
- check whether ARM or Thumb was active
    - examine bit 4 of the EmbeddedICE.DebugStatusRegister
- provide instructions to the core via ScanChain1.INSTR
- From page B-20: With the processor in the ARM state, typically the first instruction to execute is:
STMIA R0, {R0-R15}
This instruction causes the contents of the registers to appear on the data bus. You can 
then sample and shift out these values.

Reading memory: "The state of the system memory can be fed back to the debug host by using system speed 
load multiples and debug speed store multiples." (from page B-21)




## JTAG scanner using arduino

https://github.com/szymonh/JTAGscan

Does not find anything. But observing the TDO, the QCA provides some "random" patterns.
Also the RCLK (return clock) shows some activities, but very slow. Conclusion: The QCA uses adaptive clocking, and
wants a very slow clock.

adaptive clocking explained: https://www.blackhawk-dsp.com/downloads/docs/whitepapers/BHadaptiveClocking-TA-01.pdf

using 20ms half-clock-time, we get:

  10 |   8 |   9 |     f24c8ef |
+----------- SUCCESS -----------+
| TCK | TMS | TDO |      IDCODE |
+------ IDCODE complete --------+
    TCK, TMS, and TDO found.

+-- BYPASS searching, just TDI -+
| TCK | TMS | TDO | TDI | Width |
+-------------------------------+
|  10 |   8 |   9 |  11 |    32 |
+----------- SUCCESS -----------+

IDCODE explained: https://support.xilinx.com/s/article/8265?language=en_US or https://docs.amd.com/r/en-US/am011-versal-acap-trm/IDCODE-Register

0x0f24c8ef is
0000 1111 0010 0100 1100 1000 1110 1111
is
0000: version
1111 0010 0100 1100 base family code
10001110111: manufacturer code 0x477
1: per standard one

The list ends at 0x3cb https://github.com/deadsy/pycs/blob/master/wip/idcode.py
Same here: https://github.com/rdiez/Tools/blob/master/DecodeJtagIdcode/decode-jtag-idcode.pl and here
https://github.com/Merimetso-Code/JTAG-Hacking/blob/main/jlookup.py

But the JTAGscan seems to have a setup-sample issue. Using clear setup-sample-clock algorithm, the picture changes drastically:
- Reading the IDCODE works also with faster clock.
- The IDCODE is 0xB33B.
1011 0011 0011 1011
is
1011: base familiy code
001 1001 1101: manufacturer 0x19D, this would be 'Cogency Semiconductor' according to https://github.com/deadsy/pycs/blob/master/wip/idcode.py
1: per standard one

## Next steps for JTAG access

JTAG implementation (but without adaptive clocking): https://github.com/blackmagic-debug/blackmagic/blob/main/src/platforms/common/jtagtap.c

## Special TDO

The TDO only works stable (means: it reports 0b1000 in state shift-IR), if it is pulled high during power-on. If low during power-on,
it works "shortly", but stays tristate afterwards.

## The strange RTCK (aka RCLK)

The name says that it is the return clock, to be used for adaptive clocking. But it is more:
- After power-on-reset, when just trying to read what the data register shows after writing instructions 0 to 15, the RTCK
is sometimes high, sometimes low, and sometimes tristate. The state change happens with falling edge of TCLK, which happens in
state UPDATE-IR.
- INSTR = 6 -> tristate
- INSTR = 7 -> high
- INSTR = 9 -> tristate
- INSTR = 10 -> high

# How to find out the real length of the instruction register?

The reference manual DDI0222.pdf says that the instruction register is 4 bits. But seems not.
- Assume a longer instruction register, e.g. 7 bits.
- Send each possible instruction (0 to 127), and after each, read 32 bit from data register.
- Observed: 4 results are always the same.
- Conclusion: Two bits of the instruction are ignored. So the instruction register is 5 bits long.
- Now reading the data register for each of the 32 instructions (while sending 0xFF00FF00) leads to:
```
                                     (feeding FF00FF00)          (feeding FFFFFFFF) (feeding 0)
    0 -> oldInstruction is 1 data32 is 0x2E90778 <--- interesting  0xFAEDAB77        0x10000
    1 -> oldInstruction is 1 data32 is 0x0                         0x0               0x0
    2 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass           0xFFFFFFFE        0x0
    3 -> oldInstruction is 1 data32 is 0xE58477 <--- interesting   0xFAE58277        0xE18477
    4 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass           0xFFFFFFFE        0x0
    5 -> oldInstruction is 1 data32 is 0x0                         0x0               0x0
    6 -> oldInstruction is 1 data32 is 0x0                         0x0               0x8000 --> bit 15 is controllable inverted?
    7 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass           0xFFFFFFFE        0x0
    8 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass           0xFFFFFFFE        0x0
    9 -> oldInstruction is 1 data32 is 0x0                         0x0               0x0
    10 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    11 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    12 -> oldInstruction is 1 data32 is 0x0                        0x0               0x0
    13 -> oldInstruction is 1 data32 is 0x0                        0x0               0x0
    14 -> oldInstruction is 1 data32 is 0xB33B                     0xB33B            0xB33B   <--- IDCODE
    15 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    16 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    17 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    18 -> oldInstruction is 1 data32 is 0x0                        0x0               0x0
    19 -> oldInstruction is 1 data32 is 0x0                        0x0               0x0
    20 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    21 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    22 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    23 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    24 -> oldInstruction is 1 data32 is 0x0                        0x8               0x0  -> bit 3 is controllable
    25 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    26 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    27 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    28 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    29 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    30 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
    31 -> oldInstruction is 1 data32 is 0xFE01FE00 bypass          0xFFFFFFFE        0x0
```

# OpenOCD on Windows 10

Download of openOCD windows binary: https://gnutoolchains.com/arm-eabi/openocd/

Just unzip. No installation needed.
Open a command line in OpenOCD-20231002-0.12.0\bin, and just run openocd.exe

 
Initial setup:
https://openocd.org/doc-release/html/Running.html#Simple-setup_002c-no-customization

Interface config: e.g. take c232hm.cfg from the OpenOCD-20231002-0.12.0\share\openocd\scripts\interface\ftdi and copy it into the current directory.

To avoid the command line arguments: create a openocd.cfg in the current directory with the content
```
    source [find c232hm.cfg]
```

But the FT232HQ device is not detected:
```
    Error: libusb_open() failed with LIBUSB_ERROR_NOT_SUPPORTED
    Error: unable to open ftdi device with description '*', serial '*' at bus location '*'
```
Driver here: https://ftdichip.com/drivers/ but reports "everything already up to date".
Further searching: there seems to be a "Zadig tool" which is necessary to configure the FTDI driver.
https://medium.com/@manuel.bl/low-cost-esp32-in-circuit-debugging-dbbee39e508b
and
https://github.com/pbatard/libwdi/wiki/Zadig

In the Zadig:
* Menu->Options->List All Devices
* Dropdown: select "Single RS232-HS" device. It shows driver "FTDIBUS (v2.12.36.4)
* right of the green arrow, select "WinUSB" and click "Replace Driver".

Try again openocd.exe. Success, the interface is found.

But it complains that "transport is not selected", so we select JTAG (not SWD) by
adding `transport select jtag` in the c232hm.cfg.

Connecting the FT232HQ board to the QCA

Success: By Autoprobing, it finds the 5-bits-instruction register:
```
    C:\UwesTechnik\OpenOCD-20231002-0.12.0\bin>openocd.exe
    Open On-Chip Debugger 0.12.0 (2023-10-02) [https://github.com/sysprogs/openocd]
    Licensed under GNU GPL v2
    libusb1 09e75e98b4d9ea7909e8837b7a3f00dda4589dc3
    For bug reports, read
            http://openocd.org/doc/doxygen/bugs.html
    jtag
    Info : Listening on port 6666 for tcl connections
    Info : Listening on port 4444 for telnet connections
    Warn : An adapter speed is not selected in the init scripts. OpenOCD will try to run the adapter at very low speed (100 kHz).
    Warn : To remove this warnings and achieve reasonable communication speed with the target, set "adapter speed" or "jtag_rclk" in the init scripts.
    Info : clock speed 100 kHz
    Warn : There are no enabled taps.  AUTO PROBING MIGHT NOT WORK!!
    Info : TAP auto0.tap does not have valid IDCODE (idcode=0xfffffffe)
    Warn : AUTO auto0.tap - use "jtag newtap auto0 tap -irlen 5 -expected-id 0x00000000"
    Warn : gdb services need one or more targets defined
```

In the openocd.cfg, add `source [find qca7000.cfg]` and create this file.
Add there what we know:
`jtag newtap qca0tap tap -irlen 5 -expected-id 0x00000000`

Also set a clock speed to avoid the warning. See https://openocd.org/doc-release/html/Debug-Adapter-Configuration.html#jtagspeed
There is a hint regarding RCLK/adaptive clocking in https://openocd.org/doc-release/html/Config-File-Guidelines.html

Good news: In general, the ARM9 and ARM926EJS is supported by the openOCD, we find it in https://openocd.org/doc-release/html/CPU-Configuration.html, and
also a lot of target and board cfg files show the arm926.


Intermediate summary:
- The "outside" JTAG port works and shows a 5-bit instruction register, and no id-code after reset. This TAP does
  not provide RTCK.
- The ARM926 has a 4-bit-instruction register (and would have an id-code after reset?)
- We observed also situations where RTCK followed the TCLK (only with very low frequency, 40ms cycle). Not clear how this state was reached.
- So there seem to be at least to TAPs, and it needs to be found out how to reach the "inner TAP".

Access of the "child nodes": https://openocd.org/doc/html/TAP-Declaration.html and https://review.openocd.org/c/openocd/+/8041 explains the option -ir-bypass NUMBER

Low-level JTAG commands for finding out the structure of an unknown device are explained here: https://openocd.org/doc/html/JTAG-Commands.html

How to enter the commands for openOCD?

* Open puTTY.
* Host name: localhost
* Port: 4444
* Connection type: Other -> Telnet



irscan qca0tap.tap 14
drscan qca0tap.tap 32 0

```
    Open On-Chip Debugger
    > irscan qca0tap.tap 14
    > drscan qca0tap.tap 32 0
    0000b33b
```

Success: This reveals the same "idcode" from register 14 as seen with the arduino method.

Observation: After power-on-reset, the Foccci consumes 130mA on the 3.3V. After two times reading the data register `drscan qca0tap.tap 32 0`, the current decreases to 80mA. Afterwards, the result of this is 00000000, and for the first two commands it was ffffffff.
Same behavior:
- no matter whether we use 1 bit, 8 bit, 32 bit or 64 bit or 128bit.

```
(power-on-reset here)
> drscan qca0tap.tap 32 ffffffff 32 ffffffff 32 ffffffff 32 ffffffff
ffffffff
ffffffff
ffffffff
ffffffff
> drscan qca0tap.tap 32 ffffffff 32 ffffffff 32 ffffffff 32 ffffffff
ffffffff
ffffffff
ffffffff
ffffffff
(here the current drops from 130mA to 90mA)
> drscan qca0tap.tap 32 ffffffff 32 ffffffff 32 ffffffff 32 ffffffff
00000000
00000000
00000000
00000000
>
```

Checking patterns and different lengths reveals: after power-on, the data register is a 79 bit shift register.

```
(power-on-reset here)
> drscan qca0tap.tap 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff 16 0 16 0 16 0 16 0 15 0
0000
0000
0000
0000
0000
affe
feed
beef
dead
7fff
>
```

Register 0 is 27 bits wide:

```
(power-on-reset here)
> irscan qca0tap.tap 0
> drscan qca0tap.tap 27 0xaffe 27 0 27 0xaffe 27 0xdeadbe 27 0 27 0 27 0x7ffffff 27 0 27 0
03692b6a
0000affe
00000000
0000affe
00deadbe
00000000
00000000
07ffffff
00000000
>
```

Register 1:

```
(power-on-reset here)
drscan qca0tap.tap 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff
drscan qca0tap.tap 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff
drscan qca0tap.tap 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff
irscan qca0tap.tap 1
drscan qca0tap.tap 16 0 16 0 16 0 16 0 15 0
(does NOT provide the data from the "unaddressed power-on register")
drscan qca0tap.tap 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff 16 0xAFFE 16 0xFEED 16 0xBEEF 16 0xDEAD 15 0x7fff
0000
0000
0000
0000
0000
affe
feed
beef
dead
7fff -> confirms that also is register 1 is also 79 bits, but not the same content as the unaddressed.
```

Register 3:

```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (current down)
> irscan qca0tap.tap 3 (current sometimes increases, sometimes decreases by 10mA)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
fb658462
ffffffff
ffffffff
ffffffff
```
-> 27 bits. The results are stable in one power cycle, but differ a little bit after power cycle.

Register 5:

```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (current down)
> irscan qca0tap.tap 5 (no change in current)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
```
-> 79 bits. Reads all 0.

Register 6:

```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (current down)
> irscan qca0tap.tap 6 (current up again)
> irscan qca0tap.tap 6
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
00040000
00000000
00000000
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
fff00000
ffffffff
03ffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
fff00000
ffffffff
03ffffff
> drscan qca0tap.tap 32 0 32 0 32 0 32 0
00000000
fff00000
ffffffff
03ffffff
> drscan qca0tap.tap 32 0 32 0 32 0 32 0
00000000
00040000
00000000
00000000
>
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffff 32 0xffffffff
00000000
fc000000
fc000003
00000003
fc000000
ffffffff
ffffffff
ffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffff 32 0xffffffff
00000000
fff00000
ffffffff
0003ffff
fc000000
ffffffff
ffffffff
ffffffff
> drscan qca0tap.tap 32 0 32 0 32 0 32 0 32 0 32 0 32 0 32 0
00000000
fff00000
ffffffff
0003ffff
00000000
00000000
00000000
00000000
> drscan qca0tap.tap 32 0 32 0 32 0 32 0 32 0 32 0 32 0 32 0
00000000
00040000
00000000
00000000
00000000
00000000
00000000
00000000
>
```
->
- ~52 bits are fix 0. 1 bit changes sometimes.
- ~62 bits are written and get back with the next command.
- everything additional just shifted-thru

Register 9:
```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (current down)
> irscan qca0tap.tap 9 (no current change)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
> drscan qca0tap.tap 32 0 32 0 32 0 32 0 32 0 32 0 32 0 32 0
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
> drscan qca0tap.tap 32 0 32 0 32 0 32 0 32 0 32 0 32 0 32 0
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
>
```
-> all zeros. No length determination possible.

Register 12:
```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (current down)
> irscan qca0tap.tap 12 (massive current increase, sometimes from 80mA to 260mA. Sometimes 160mA, sometimes lower)
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
ffffffff
ffffffff
ffffffff
ffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
00000000
ffff8000
ffffffff
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
00000000
00000000
ffff8000
ffffffff
```
-> also 79 bits

This bit controls the current. off->80mA, on->150mA.
In an other power cycle, the same bit switches between 90mA and 290mA.
`> drscan qca0tap.tap 32 0 32 0 32 0x1000 32 0`
In an other power cycle, another bit controls the current bitween 80mA and 140mA.
`> drscan qca0tap.tap 32 0 32 0x1000 32 0`

Selecting register 13 turned the high current off in these cases.
- 1, 13 -> off, 12 -> stays off.
- 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25 -> temporary off, 12 -> high current again.
- 12, 18, 19: high current (while 18 and 19 have ~20mA more than 12)
- 19 activates the high current, which was blocked by the 1 or 13 instruction. Afterwards 12 and 18 work again to activate the current.



Register 13:
```
(power-on-reset here)
> irscan qca0tap.tap 13
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
.....
```
-> to be found out

Register 14:
```
(power-on-reset here)
> irscan qca0tap.tap 14
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
```
-> also 79 bits

Häää? This should be the ident????
Again:
```
(power-on-reset here)
> irscan qca0tap.tap 14
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff (lowers the current and the RCLK goes low)
```
does NOT show the ident.

```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff
> irscan qca0tap.tap 14 (lowers the current and the RCLK goes low)
> drscan qca0tap.tap 32 0xffffffff
```
does NOT show the ident.

```
(power-on-reset here)
> drscan qca0tap.tap 32 0xffffffff
> drscan qca0tap.tap 32 0xffffffff (lowers the current and the RCLK goes low)
> irscan qca0tap.tap 14 
> drscan qca0tap.tap 32 0xffffffff 
```
0xb33b.


Register 18:
```
(power-on-reset here)
> irscan qca0tap.tap 18
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
```
Register 19:
```
(power-on-reset here)
> irscan qca0tap.tap 19
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
```
Register 24:
```
(power-on-reset here)
> irscan qca0tap.tap 24
> drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff 32 0xffffffff
```


### Re-activation of the PLC communication

by writing IR. Example: reset, DR, DR leads to deactivation of the PLC communication. The
PLC communication can be re-activated by IR=23, but only in certain preconditions. E.g. IR=24 IR=23
works.

- 0, 23 no
- 1, 23 no
- 2, 23 no
- 3, 23 no
- 4, 23 no
- 5, 23 no
- 6, 23 yes
- 7, 23 yes
- 8, 23 yes
- 9, 23 yes
- 10 does not even disable the communication. 0, 10, 23 does NOT enable the PLC communication.
- 11, 23 yes
- 12, 23 no
- 13, 23 yes
- 14 similar to 10. No disable PLC, no enable. Reading the DR value 0xb33b works while PLC is working.
- 15, 23 yes
- 16 No disable PLC. Enables PLC when it was disabled with 15. But does not enable with sequence 0, 15, 16.
     Rescued with 15, 24, 23 -> PLC works again.
- 17, 23 yes
- 18, 23 no. 18 causes high current. Rescued with 24, 23 -> PLC works again.
- 19, 23 no. 19 causes high current. Rescued with 24, 23 -> PLC works again.
- 20, 23 no. PLC stuck after some tests with different combination. Rescued with 13, 24, 23.
- 21 does not stop PLC
- 22 does not stop PLC
- (23 depends on the preconditions)
- 24, 23 yes
- 25 and 26 and 27 and 28 similar to 10. No disable PLC, no enable.
- 29, 23 yes
- 30 and 31 similar to 10. No disable PLC, no enable.

## Entry sequence after power on
In general, after power-on, the current reduces and the floating RCLK turns to low, if
- two scan-dr or
- two scan-ir or
- a combinatin of one scan-dr and one scan-ir
is sent.
Also the PLC communication stops at this point.

## Analog supply control
The 1.6V on the TX and RX path are shifting independent. E.g.
IR=1 both off
IR=24 TX on, RX off
TR= .... 19: both on

## Pin control
The INT, R3(GPIO1) and R4(GPIO2) can be controlled together by this sequence:
DR-DR-IR1-IR2-IR3-IR2-IR4-IR2

The GPIO2 can be controlled by writing DR without any IR.
power on
drscan qca0tap.tap 32 0 32 0x100000 32 0 32 0 (first ignored, but necessary)
drscan qca0tap.tap 32 0 32 0x100000 32 0 32 0 (second ignored, but necessary. Turns INT, GPIO1 and GPIO2 to weak low)
drscan qca0tap.tap 32 0 32 0x100000 32 0 32 0 high
drscan qca0tap.tap 32 0 32 0x000000 32 0 32 0 low

Further pin controls
(outputs observed: INT.GPIO1.GPIO2.RX.TX)

- power-on-reset
- drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff
- drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff (outputs 11100)
- irscan qca0tap.tap 0 (outputs 10001, sometimes 00001)

- drscan qca0tap.tap 32 0x080 This bit controls the output enable of the GPIO1 (changes between weak and strong low).
- drscan qca0tap.tap 32 0x100 GPIO1 = H
- drscan qca0tap.tap 32 0x180 GPIO1 = float
- drscan qca0tap.tap 32 0x000 GPIO1 = L
- drscan qca0tap.tap 32 0x080 GPIO1 = float

- drscan qca0tap.tap 32 0x200 GPIO2 = H (or float, to be measured)
- drscan qca0tap.tap 32 0x400 GPIO2 = H (or float, to be measured)

- drscan qca0tap.tap 32 0x2000 FL_CS changes to H (or pull-up?)
- drscan qca0tap.tap 32 0x4000 FL_CS changes to H (or pull-up?)
- drscan qca0tap.tap 32 0x8000 FL_MOSI changes to H
- drscan qca0tap.tap 32 0x80000 FL_MISO changes to H
- (not found a bit which would control the FL_CLK)

- drscan qca0tap.tap 32 0x10000000 INT changes to high impedance
- drscan qca0tap.tap 32 0x20000000 INT changes to H

### Reading pin state

Preparation:
- power-on-reset
- drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff
- drscan qca0tap.tap 32 0xffffffff 32 0xffffffff 32 0xffffffff (outputs 11100)
- irscan qca0tap.tap 0 (outputs 10001, sometimes 00001)

Actual reading:
- drscan qca0tap.tap 32 0x10000000 (control INT to tristate)
- 00810000 when INT is externally pulled low
- drscan qca0tap.tap 32 0x10000000 (control INT to tristate)
- 01810000 when INT is externally pulled high

- drscan qca0tap.tap 32 0xffffffff (control all to tristate)
- fbedab77 when GPIO1 is low
- drscan qca0tap.tap 32 0xffffffff
- fbedab7f when GPIO1 is high

Conclusions:
* IR=0 selects a scan path for reading and writing the pins.
* The pins have two control bits, which select between H, L and tristate.
* The read-back state (H or L) is at the higher bit position.

## Further JTAG investigations

with TRST=L
 we see heavy activity on RTCK, slower than the 1kHz clock, if we try auto-probing with 1kHz clock.

This works in both cases of TDO pulling: pull-up and pull-down.

Next step: How to use slower clock or adaptive clocking with openOCD?

- step 1: in the interface config of openOCD, set the clock speed to zero, to enable adaptive clocking: "adapter speed 0".
- step 2: https://ftdichip.com/wp-content/uploads/2024/09/DS_FT232H.pdf says: "The FT232H will assert the TCK line and wait for the RTCK to be returned from the target device to GPIOL3 line before changing the TDO (data out line)." We connect the RTCK to the AD7, because the cfg files says "ftdi layout_signal GPIOL3 -data 0x0080 -oe 0x0080"

Result: The FT232HQ adapts the TCK according to the feedback on RTCK.

The slow RCLK disappears (sometimes) after power-on-reset.

It re-appears after the following sequence:
- precondition: TDO pulled high.
- pull TRST to high
- configure openODC to use 1kHz clock (without adaptive clocking): "adapter speed 1"
- run openOCD without configured taps. Just auto-probing. This finds the 5-bit-TAP.
- pull TRST to low
- configure openOCD to use adaptive clocking: "adapter speed 0"
- run openOCD. Now we see clocks on TCK and RTCK with 1 to 3ms on- and off-time.
- it does not find TAPs: Error: JTAG scan chain interrogation failed: all ones

Conclusion: This is a state where slow module is between the TCK and the RTCK, but it does not show anything on TDO.

### Variation points

1. TRST pulled low or high
2. TDO pulled low or high during power-on
3. System-Reset: (a) not used, (b) released before TRST, (c) released after TRST
4. Timing of power-on, system-reset, TRST, first TCK
5. Line-swaps between data sheet and real world

### Observed TAPs

- TAP5bit:
    - precondition: TRST=H, TDO=pullup
    - observation: 5-bit-TAP. Works for boundary scan, aka control and read pin states.
- TAPslow:
    - precondition: some actions on TAP5bit (maybe just reading twice). Then pull TRST low. Enable adaptive clocking.
    - observation: adaptive clocking forces very slow clock (~2 to ~6ms cycle time). No activity on TDO.
    - todo: does the slow timing relate to SPI transfers to flash or host?
- TAParm: Should be a 4-bit-TAP.
    - preconditions
        - TDO=270k pulldown
        - TRST=2k pullup
        - TRST not connected to jtag adapter
        - SRST not connected to jtag adapter
        - openOCD configured to use adaptive clocking: "adapter speed 0"
        - RTLK connected to AD7 of the FT232H, which is the return clock input of the adapter.
        - power-on the QCA
        - connect the FT232H to the PC
    - observation: clock cycle time is between multiple milliseconds and 170ns (~6MHz), and shows the expected 4-bit instruction register and ID code:

```
    Info : RCLK (adaptive clock speed)
    Warn : There are no enabled taps.  AUTO PROBING MIGHT NOT WORK!!
    Warn : Haven't made progress in mpsse_flush() for 2026ms.
    Info : JTAG tap: auto0.tap tap/device found: 0x07926477 (mfg: 0x23b (ARM Ltd), part: 0x7926, ver: 0x0)
    Warn : AUTO auto0.tap - use "jtag newtap auto0 tap -irlen 4 -expected-id 0x07926477"
```

- limitations:
        - The TAParm is not visible while SRES is hold low. In this state, the debug adapter waits for the RTCK, and this works as soon as SRES is released.
        - The TAParm disappears when TRST is pulled low, and even stays away if the TRST is high again. This does not "heal" by applying SRST. It "heals" by a power-on-reset of the QCA.
        
## Debugging with openOCD and GDB (Gnu Debugger)

### Installation of GDB on Windows 10

(Ref: https://stackoverflow.com/questions/67574925/update-gdb-version-on-windows-10)
- Install MSYS2
- in MSYS2, use pacman to install gdb: in msys2 terminal pacman -S --needed base-devel mingw-w64-x86_64-toolchain and you can then choose the packages you wish to install (including gdb and gdb-multiarch)
- add the path to msys2 to the windows search path
- open a new command window (git shell or CMD). gdb --version should work.


### First steps with GDB

- start openOCD. It should find the target.

```
C:\LegacyApp\openocd\OpenOCD-20250710-0.12.0\bin>openocd.exe
Open On-Chip Debugger 0.12.0 (2025-07-10) [https://github.com/sysprogs/openocd]
Licensed under GNU GPL v2
libusb1 d52e355daa09f17ce64819122cb067b8a2ee0d4b
For bug reports, read
        http://openocd.org/doc/doxygen/bugs.html
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
Info : RCLK (adaptive clock speed)
Info : JTAG tap: qca7000.cpu tap/device found: 0x07926477 (mfg: 0x23b (ARM Ltd), part: 0x7926, ver: 0x0)
Info : Embedded ICE version 6
Info : qca7000.cpu: hardware has 2 breakpoint/watchpoint units
Info : [qca7000.cpu] Examination succeed
Info : [qca7000.cpu] starting gdb server on 3333
Info : Listening on port 3333 for gdb connections
```

- In a new shell: `gdb-multiarch.exe` (Do not run gdb.exe, it does not have the support for ARM.)
- or better `winpty gdb-multiarch.exe` which allows layouts (TUI) in the git bash.
- `tar ext :3333`
- `dump binary memory testdump0000_128k.bin 0x0 0x20000` dumps 128k from address 0x0 into the specified file.
- `layout asm` to show the disassembly window
- `c` to continue
- `ctrl-c` to halt
- `break *0x12a76` to set a breakpoint at a certain address
- `hbreak *0x255e4c` to set hardware breakpoint
- `hbreak *0x258706` to set hardware breakpoint in sendResponseForA088_VS_CLASSIFICATION()

## Controlling openOCD from python

docu: https://gitlab.zapb.de/openocd/python-openocd
installation from cmd: pip install openocd

# QCA firmware hacking DEF CON 33

- authors: jan.berens@alpitronic.it, marcell.szakaly@cs.ox.ac.uk
- reference: https://arxiv.org/abs/2404.06635

https://openinverter.org/forum/viewtopic.php?p=86171#p86171
https://youtu.be/SQz4nySj4hg

- at 32:24 e.g. NVM Manifest, NVM Softloader, Memory Control, different types of firmware packages.
- Assumed boot sequence
- use SPI read (-address) to dump the bootloader image
- reverse the bootloader
- LZMA is the compression method of the firmware
- They created custom firmware to run DOOM (receiving keyboard via UDP and sending video frame via UDP).


## PIB layout

Undocumented security bit at offset 0x1F8C: 0 = remote reading and writing allowed, 1 = remote reading and writing blocked.
The offset of the raw pib is different (as shown at 20:44 in the video)

xxd edited.pib | grep 00002340

In the video they mark the byte at 0x234C.

# Security analysis

## Is it possible to read and write PIB remotely?

Precondition: QCA7005 (on Foccci) as EV, and AR4720 with pyPLC as EVSE.

Step 1: Read the software versions of all modems in the network

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 -r broadcast
eth0 FF:FF:FF:FF:FF:FF Request Version Information
eth0 98:48:27:5A:3C:E4 QCA7420 MAC-QCA7420-1.4.0.20-00-20171027-CS
eth0 04:65:65:FF:FF:FF QCA7005 MAC-QCA7005-1.1.0.730-04-20140815-CS
```

Step 2: Read the software version of the remote device

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -r
eth0 04:65:65:FF:FF:FF Request Version Information
eth0 04:65:65:FF:FF:FF QCA7005 MAC-QCA7005-1.1.0.730-04-20140815-CS
```

Step 3: read the device attributes

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -a
eth0 04:65:65:FF:FF:FF Fetch Device Attributes
eth0 04:65:65:FF:FF:FF QCA7005-MAC-QCA7005-1.1.0.730-04-20140815-CS (1mb)
```

Step 4: read the flash memory parameters (of the SPI flash chip)

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -f
eth0 04:65:65:FF:FF:FF Fetch NVRAM Configuration
eth0 04:65:65:FF:FF:FF TYPE=0x14 (M25P16_ES) PAGE=0x0100 (256) BLOCK=0x10000 (65536) SIZE=0x200000 (2097152)
```

Step 5: read the PIB header

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -I
	PIB 0-0 8080 bytes
	MAC 04:65:65:FF:FF:FF
	DAK 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00 (none/secret)
	NMK 77:77:AB:22:77:77:77:77:77:77:77:77:77:77:77:77
	NID 01:02:03:04:05:06:07
	Security level 0
	NET Qualcomm Atheros Enabled Network
	MFG Qualcomm Atheros HomePlug AV Device
	USR YURA CCM SOP DEFAULT
	CCo Never
	MDU N/A
```

Step 6: read the powerline link status (?)

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -L
eth0 04:65:65:FF:FF:FF Request Version Information
eth0 04:65:65:FF:FF:FF 1
```

Step 7: read the network membership information

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -m
eth0 04:65:65:FF:FF:FF Fetch Network Information
eth0 04:65:65:FF:FF:FF Found 1 Network(s)

source address = 04:65:65:FF:FF:FF

	network->NID = 01:02:03:04:05:06:07
	network->SNID = 9
	network->TEI = 2
	network->ROLE = 0x00 (STA)
	network->CCO_DA = 98:48:27:5A:3C:E4
	network->CCO_TEI = 1
	network->STATIONS = 1

		station->MAC = 98:48:27:5A:3C:E4
		station->TEI = 1
		station->BDA = B8:27:EB:E6:39:89
		station->AvgPHYDR_TX = 009 mbps Primary
		station->AvgPHYDR_RX = 009 mbps Primary
```

Step 8: read the firmware. This is denied.

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -n firmwaredump.nvm
eth0 04:65:65:FF:FF:FF Read Module from Memory
eth0 04:65:65:FF:FF:FF Module not available in NVM or Memory (0x32): Device refused request
```

Step 9: read the parameters (PIB). This works.

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -p parameterdump.pib
eth0 04:65:65:FF:FF:FF Read Module from Memory
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -p parameterdump2.pib
eth0 04:65:65:FF:FF:FF Read Module from Memory
pi@RPi2023:~/myprogs/open-plc-utils $ ls -al parameterdump.pib 
-rw-r--r-- 1 pi pi 9040 17. Sep 15:34 parameterdump.pib
```

Step 9b: check whether the "remote protection flag" at 0x234c is set. No, it is zero.

```
pi@RPi2023:~/myprogs/open-plc-utils $ xxd parameterdump.pib | grep 00002340
00002340: 0100 0000 0000 0000 0000 0000 0000 0000  ................
```


Step 10: write the PIB. This works.

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -P parameterdump2.pib
eth0 04:65:65:FF:FF:FF Start Module Write Session
eth0 04:65:65:FF:FF:FF Flash parameterdump2.pib
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000000
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000578
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000AF0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00001068
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x000015E0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00001B58
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 640
MODULE_OFFSET 0x000020D0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 640
MODULE_OFFSET 0x02800000
eth0 04:65:65:FF:FF:FF Close Session
eth0 04:65:65:FF:FF:FF Reset Device
eth0 04:65:65:FF:FF:FF Resetting ...
```

Step 11: Apply Factory Defaults. This works, but seems not to change something important. Charging still works, also after a power-on-reset.

```
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -T
eth0 04:65:65:FF:FF:FF Restore Factory Defaults
eth0 04:65:65:FF:FF:FF Restoring ...
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -p parameterdump_afterFactoryDefault.pib
eth0 04:65:65:FF:FF:FF Read Module from Memory
pi@RPi2023:~/myprogs/open-plc-utils $ plctool -ieth0 04:65:65:FF:FF:FF -I
	PIB 0-0 8080 bytes
	MAC 04:65:65:FF:FF:FF
	DAK 00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:00 (none/secret)
	NMK 77:77:AB:22:77:77:77:77:77:77:77:77:77:77:77:77
	NID 01:02:03:04:05:06:07
	Security level 0
	NET Qualcomm Atheros Enabled Network
	MFG Qualcomm Atheros HomePlug AV Device
	USR YURA CCM SOP DEFAULT
	CCo Never
	MDU N/A
pi@RPi2023:~/myprogs/open-plc-utils $ 
```

Step 12: Is it possible to patch the "remote protection flag" in the PIB using hex editor?

No. The plctool complains about wrong checksum.

```
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ cp parameterdump_ioniq.pib edited.pib
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ ghex edited.pib 
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ xxd edited.pib | grep 00002340
00002340: 0100 0000 0000 0000 0000 0000 0100 0000  ................
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ plctool -ieth0 04:65:65:FF:FF:FF -P edited.pib
plctool: pibfile2 found bad image checksum in edited.pib module 1
```

Step 13: Is it possible to set the "remote protection flag" using setpib? Yes. Patching logical address 0x1F8C leads to the intended
change at physical 0x234C. Writing and reading-back works, also after Power-On-Reset. So the used (quite old) firmware seems
to ignore the "remote protection flag" completely.

```
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ cp parameterdump_ioniq.pib edited.pib
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ xxd edited.pib | grep 00002340
00002340: 0100 0000 0000 0000 0000 0000 0000 0000  ................
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ setpib edited.pib 1F8C byte 1
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ xxd edited.pib | grep 00002340
00002340: 0100 0000 0000 0000 0000 0000 0100 0000  ................
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ plctool -ieth0 04:65:65:FF:FF:FF -P edited.pib
eth0 04:65:65:FF:FF:FF Start Module Write Session
eth0 04:65:65:FF:FF:FF Flash edited.pib
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000000
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000578
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00000AF0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00001068
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x000015E0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x00001B58
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 1400
MODULE_OFFSET 0x05780000
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x11
MOD_OP_DATA_LEN 1423
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 640
MODULE_OFFSET 0x000020D0
MSTATUS 0x0000
ERROR_REC_CODE 0
RESERVED 0x00000000
NUM_OP_DATA 1
MOD_OP 0x00
MOD_OP_DATA_LEN 23
RESERVED 0x00000000
MODULE_ID 0x7002
MODULE_SUB_ID 0x0000
MODULE_LENGTH 640
MODULE_OFFSET 0x02800000
eth0 04:65:65:FF:FF:FF Close Session
eth0 04:65:65:FF:FF:FF Reset Device
eth0 04:65:65:FF:FF:FF Resetting ...
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ plctool -ieth0 04:65:65:FF:FF:FF -p readagain.pib
eth0 04:65:65:FF:FF:FF Read Module from Memory
pi@RPi2023:~/myprogs/Ioniq28Investigations/CCM_ChargeControlModule_PLC_CCS/QCA_Analysis $ xxd readagain.pib | grep 00002340
00002340: 0100 0000 0000 0000 0000 0000 0100 0000  ................
```


# References

- ref1: JTAG Router, JTAG Route Controller (JRC), enabling and disabling TAPS https://openocd.org/doc/html/TAP-Declaration.html chapter 10.6

