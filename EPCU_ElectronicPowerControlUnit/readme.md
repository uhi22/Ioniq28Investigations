# EPCU

Contains the motor inverter and the 12V DCDC

The main controller board and parts of the inverter gate driver board:

![image](20240624_EPCU_opened.jpg)

## Controller board

- Black connector to DCDC boards
- big white connector CN1005 to the inverter gate driver board
- small white connector CN1004 to the phase current sensors
- 4x16 pin connector CN1000 to the cable harness

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
- temperature sensor R147 at CN200 pins 2 (red) and 3 (gray), with ~12k at room temperature.
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
