# EPCU

Contains the motor inverter and the 12V DCDC (aka LVDC aka LDC).

The main controller board and parts of the inverter gate driver board:

![image](20240624_EPCU_opened.jpg)

## Controller board

- Black connector CN1002 to DCDC boards
- big white connector CN1005 to the inverter gate driver board
- small white connector CN1004 to the phase current sensors

### CN1000 Harness Connector

- 4x16 pin connector CN1000 to the cable harness. The numbering is printed inside the connector. Letters A to Q (with I missing) and rows 1 to 4.

- A1 sine wave 10kHz, between 2V and 12V. The resolver exitation.
- B1 sine wave inverse to A1.
- J1+K1 PCAN?, connected to two transceivers U9002 and U9003.
- L1+M1 diag CAN?, connected to two transceivers U9001 and U9000.
- O1 Data line U9500 "ST L9637" ISO9141 "K-Line" transceiver. https://www.st.com/en/automotive-analog-and-power/l9637.html
- Q1 GND

- M2+N2 spare CAN, not populated L9003, U9005.
- P2, Q2 GND

- P3 wakeup line. 12V to enable the power supply of the board.
- Q3 12V

- F4, G4 bus choke L2601
- P4, Q4 12V

### Power Supply

The 12V power comes via the harness connector Q3, P4, Q4.
Reverse-polarity diodes D1100 and D1101.
U1100 TLE7368E provides different voltages: 5V, 3.3V and 1.5V. https://www.infineon.com/dgdl/Infineon-TLE7368-DataSheet-v02_60-EN.pdf?fileId=5546d46258fc0bc1015969d271b041d1
The TLE7368E needs a high signal on pin 10 "Enable Input Ignition Line". This is TP1105 (on back side), which is feed from CN1000.P3 via
D1105 and R1101 and R1102.

By connecting CN1000.P3 and Q3 to 12V, the EPCU starts to draw power (400mA at 12V) and the CANs are sending data.

### CAN busses

The EPCU contains two external available CAN busses, and two internal control units (Motor Controller "MCU" and Vehicle Controller "VCU"). Both
control units are connected to both CAN busses, so the EPCU has four CAN transceivers.

"Left CAN" TP9004:
```
0x2C1 in 1ms cycle with 00 00 FF 7F 00 00 00 00 
0x232 in 1ms cycle with 00 00 00 00 00 00 00 00 
0x58F in 100ms cycle with 08 40 00 00 00 00 40 1F 
```

"Right CAN" TP 9008: A lot of messages, 0x109, 0x200, 0x201, 0x202, 0x291, 0x2A1, 0x523, 0x524, 0x540, 0x549, 0x579, 0x57A, 0x57B, 0x590, 0x592, 0x5DC, 0x5DE


Todo: Measure on the TX pin of each transceiver, which control unit sends which data on which CAN.


## Gate driver board

- 6 gate drivers, 32 pin
- The IGBTs have 4 pins, e.g. UNG, UNE, UNS, UNA (for the U phase, Negative side). 

## DCDC (LVDC)

The DCDC converter boards, with transformator and choke in between:

![image](20240624_EPCU_DCDC.jpg)


Primary side:
- Fuse HINODE 600SFK30M1J
- Filter with double choke and 3 x 1.5µF/630V MKP
- Full bridge (Q1, Q2, Q3, Q4), with gate drivers Q300, Q301, Q302, Q303
- Controlled via the 4-pin connector CN103 via isolation transformers
- Current measurement transformer with 1 turn primary winding, and rectification D107, D108, D111
- Current measurement signal on two-pin connector CN102. Wires orange and black/white.
- two diodes D109, D110 on the back side, STM STTH8R06GY. 630V, 30A, ultrafast. They clamp the CN105 between the DC rails.
- two inductors 1.8µH in series between one leg of the H-bridge (Q2 drain and Q1 source) and CN105.

Transformer in the middle: P/N TR47-413-260HM3A

Secondary side:
- middle of the secondary winding is connected via choke to the +12V
- both sides of the secondary winding go the the drains (cathodes of the body diodes)
- active rectification with 4 x FDB075N15A  (Fairchild,onsemi) Power Field-Effect Transistor, 120A, 150V, 0.0075ohm, N-Channel
- two in parallel in each branch
- controlled via the 6-pin connector CN201
- temperature sensor R146 at CN201 pins 5 (black) and 6 (orange), with ~12k at room temperature.
- temperature sensor R147 at CN200 pins 2 (red) and 3 (gray), with ~12k at room temperature. This is the temperature on PCAN 0x523 byte 2 and also byte 3. The red wire sits at ~3.3V at room temperature, and when applying 100k additional pull-down, the temperature on CAN increases from 21°C to 24°C.
- voltage probing via CN200 pin 1 (white, ground) and 4 (violet, 12V)
- low voltage ground is directly the aluminium case

## Phase Current Sensor

8-pin-connector, 6 wires used.

## DC capacitor

The ports for the input, LVDC, IGBT module and discharge resistor are just connected in parallel.
The discharge resistor has 70kohm / 10W. It causes 5mA or 1.75W at 350V.


## References

* Ref1 some reverse-engineered pin-outs https://openinverter.org/forum/viewtopic.php?p=77179#p77179
* Ref2 unsorted collection of pictures of the EPCU https://hnng.de/ioniq/pics/epcu/
* Ref3 Discussion and some pictures on the goingelectric forum https://www.goingelectric.de/forum/viewtopic.php?f=116&t=93269
