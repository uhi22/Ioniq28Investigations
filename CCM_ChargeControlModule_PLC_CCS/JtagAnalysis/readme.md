# JTAG trace of MPC5605B together with ISystem IC3000

Recorded with: Saleae Logic 2, version 2.4.6

- t=5280ms: Power-on of the target, some playing around.
- t= 65s, 68s, 70s: a series of three resets, made by pressing "reset" in the ISystems GUI (winIDEA). The memory window was setup to show some bytes at address 0x00.
- Afterwards: Read 4kByte from 0x00 (code flash) and read 4kByte from 0x80'0000 (data flash) and store it into files.

