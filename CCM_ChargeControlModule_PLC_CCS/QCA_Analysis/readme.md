
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

## Conclusion 1: The firmware images (also on the SPI flash) are "packed".

They do not contain ARM instruction. Seems that the bootloader "unpacks" them into the RAM to get the real executable code.

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

In general, after power-on, the current reduces and the floating RCLK turns to low, if
- two scan-dr or
- two scan-ir or
- a combinatin of one scan-dr and one scan-ir
is sent.


