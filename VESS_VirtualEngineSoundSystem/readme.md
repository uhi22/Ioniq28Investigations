# VESS

Reads the speed and the gear selection from CAN, and sends an engine sound and reverse-bing to a speaker

![image](VESS_20250131_01.jpg)
![image](VESS_20250131_02.jpg)
![image](VESS_20250131_03.jpg)
![image](VESS_20250131_04.jpg)
![image](VESS_20250131_05_audioamp.jpg)
![image](VESS_20250131_06_controller.jpg)

YAMAHA YMF827B see Ref6
![image](VESS_20250131_07_yamaha_sound.jpg)

SPI Flash SPANSION FL116 KVF01 (or KVE01?) S25FL116K 16 MBit see Ref5
![image](VESS_20250131_08.jpg)

![image](VESS_20250131_09_NCV8141_linear_regulator.jpg)
![image](VESS_20250131_10_pcb_backside.jpg)
![image](VESS_20250131_11_pcb_frontside.jpg)


## Harness Connector

- 2x6 pin

- 1 (green) PCAN L
- 2 (orange) PCAN H
- 3 (black) ground
- 4 (vio) VESS button to ground
- 5 (red) +12V
- 6 (white) VESS speaker +
- 7 nc
- 8 nc
- 9 (black) ground
- 10 nc
- 11 (blue) VESS LED to ground
- 12 (brown) VESS speaker -

## CAN communication


### Diagnostic Communication


## References

* Ref1 Youtube and github for the Kona VESS https://youtu.be/OLT1aKdpYhs and https://github.com/ereuter/vess
* Ref2 goingelectric: installation position of VESS control unit and speaker
* Ref3 schematic of the VESS integration https://service.hyundai-motor.com/UPLOAD/data/Passenger/HY/HME/DEU/ETM-IMAGES/HY-AE22-IMAGES-DEU/eaeevsd17314ag.svg
* Ref4 internal block diagram of the VESS https://www.goingelectric.de/forum/viewtopic.php?p=540312#p540312
* Ref5 data sheet of the SPI flash https://www.mouser.com/datasheet/2/380/S25FL116K_00-274912.pdf?srsltid=AfmBOooF0maW2Ar8tsxoBHCp190RUxyHD0BjgixwFOKB7HmAxDmbMZNP
* Ref6 sound generator YAMAHA https://device.yamaha.com/en/lsi/products/sound_generator/