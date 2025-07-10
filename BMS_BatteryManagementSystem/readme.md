

## Part numbers

The Hyundai Ioniq 28kWh battery can have the following stickers on the case;

- 37501 G7200
- 37501 G7250

Incase your battery is missing some wires/disconnect switches, here are the OEM part numbers and purchase links. Do note that it might be cheaper to source from your local scrapyard!
|  Product |  Purchase Link |
| :--------: | :---------: |
| Service disconnect switch E437586000 |  [Ebay](https://www.ebay.co.uk/sch/i.html?_from=R40&_trksid=p2332490.m570.l1313&_nkw=E437586000&_sacat=0)   |
| HV cable, 91662-K4500 |  x  |
| HV connector, Yura 110WP 2F, 18790 11883 |  KIA dealer, 11€ (Only has interlock, no HV pins)  |
| Low voltage connector KET MG656922-5 (requires [C025](https://m.alibaba.com/x/AxdkCn?ck=pdp) and [C060](https://m.alibaba.com/x/AxdkCS?ck=pdp) pins) |  [Alibaba](https://m.alibaba.com/x/AxdkBM?ck=pdp)  |

## Battery specifications
The battery has 96 cells in series, nominal voltage of 370V, with 28kWh capacity

## CAN messages
The BMS requires the following CAN messages to operate

- 0x200 (10ms, Contains contactor closing request)
- 0x523 (10ms)
- 0x524 (10ms)
- 0x553 (100ms)
- 0x57F (100ms)
- 0x2A1 (100ms)

The byte3&5 in the CAN message 0x200 contains the request to close contactors

The BMS sends the following CAN messages when it operates:

- 0x4E2 (100ms)
- 0x594 (100ms, SOC, allowed charge/discharge power)
- 0x595 (100ms, battery voltage and current)
- 0x596 (100ms, 12V voltage, min/max temperatures)
- 0x597 (100ms)
- 0x598 (100ms)
- 0x599 (100ms)
- 0x59C (100ms)
- 0x59E (100ms)
- 0x5A3 (100ms)
- 0x542 (100ms, SOC display)
- 0x491 (100ms)
- 0x493 (100ms)
- 0x5D5 (Power relay temperature)
- 0x5D8
- 0x5D7

### Active polling of data

The battery can be queried by polling it with 0x7E4 requests. The battery replies on ID 0x7EC

The battery can be queried for 5 different multiframe groups. The polling message looks like this:

  CAN_frame IONIQ_7E4_POLL = {.FD = false,
                              .ext_ID = false,
                              .DLC = 8,
                              .ID = 0x7E4,
                              .data = {0x02, 0x21, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00}};

The 2nd byte (0x01) determines which group gets polled. The BMS replies to 0x01-0x05. It is OK to ask for a new group every 250ms.

Battery relay status, mode, and all individual cellvoltages can be read via this active polling. An example on how to do this can be found on the [Battery-Emulator repository](https://github.com/dalathegreat/Battery-Emulator)