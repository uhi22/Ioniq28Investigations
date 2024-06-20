
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

## Next steps for JTAG access

JTAG implementation (but without adaptive clocking): https://github.com/blackmagic-debug/blackmagic/blob/main/src/platforms/common/jtagtap.c

