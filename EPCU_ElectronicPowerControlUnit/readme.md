# EPCU

Contains the motor inverter and the 12V DCDC

Discussion and some pictures here: https://www.goingelectric.de/forum/viewtopic.php?f=116&t=93269


The main controller board and parts of the inverter gate driver board:

![image](20240624_EPCU_opened.jpg)

# Controller board

- Black connector to DCDC boards
- big white connector to the inverter gate driver board
- small white connector maybe case temperature sensors
- 4x16 pin connector to the cable harness

# Gate driver board

- 6 gate drivers, 32 pin
- The IGBTs have 4 pins, e.g. UNG, UNE, UNS, UNA (for the U phase, Negative side). 

# DCDC

The DCDC converter boards, with transformator and choke in between:

![image](20240624_EPCU_DCDC.jpg)


Primary side:
- Full bridge (Q1, Q2, Q3, Q4), with gate drivers Q300, Q301, Q302, Q303
- Controlled via the 4-pin connector CN103
- maybe gate driver supply via the two-pin connector and small transformer

Transformer in the middle

Secondary side:
- middle of the secondary winding is connected via choke to the +12V
- both sides of the secondary winding go the the drains (cathodes of the body diodes)
- active rectification with 4 x FDB075N15A  (Fairchild,onsemi) Power Field-Effect Transistor, 120A, 150V, 0.0075ohm, N-Channel
- two in parallel in each branch
- controlled via the 6-pin connector CN201
- maybe voltage and current probing via CN200
- low voltage ground is directly the aluminium case