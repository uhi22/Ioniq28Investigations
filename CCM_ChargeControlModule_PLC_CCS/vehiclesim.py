"""Vehicle simulation for running a complete CCS charging session with the Ioniq CCM on the bench.

Connect the CCM CAN to a PEAK PCAN adapter (500 kBaud), and the CCM CP/PE to a charger
simulation (e.g. pyPLC in EVSE mode). Then switch on the CCM and start this script. The CCM
runs SLAC, the V2G session and the CurrentDemand loop, with the target current given here.

Sent every 100 ms (content from the car trace ioniq2018_motorCAN_500k_HPC.asc):
  0x57F  static                                    needed for SLAC
  0x597  B0 bit 7 toggle bit, B7 0 -> 2            needed for SLAC
  0x599  B0, B1, B2 SOC 0.5 %, B7 bit 0 CCS trigger needed for SLAC
  0x5A3  static                                    needed for ChargeParameterDiscovery
  0x59C  B2..B3 target voltage 0.1 V,              needed for PreCharge and CurrentDemand.
         B4..B5 target current 0.1 A (LE16)        The CCM forwards it 1:1 as EVTargetCurrent.
  0x59E  B0..B1 remaining time to full SOC in s,   not needed for the session, but for a real charger:
         B2..B3 remaining time to bulk SOC in s,   forwarded as RemainingTimeToFullSoC/ToBulkSoC and
         B6..B7 maximum power (9800 = 98 kW)       EVMaximumPowerLimit (without 0x59E: 0 kW!)

The vehicle reacts on the CCM progress (0x5E9 B0 bits 1..7, CCM_ChargeProgress) like the car.
See readme.md, chapter "Running a complete charging session on the bench".
(Derived from tools/vehiclesim.py of https://github.com/uhi22/ioniq-chargepower-reducer,
where also the investigation is documented, in doc/bench-testing.md.)

Requires: pip install python-can, and the PEAK driver (PCANBasic.dll).

Usage:
  python vehiclesim.py                          # 90 s, target current 50 A
  python vehiclesim.py -d 120 --current 0:60,20:30,40:80
      current profile: seconds after the start of CurrentDemand : current in A
"""
import argparse
import time

import can

CYCLE_S = 0.1
RAMP_A_PER_CYCLE = 1.0         # like the car: 10 A/s
BATTERY_VOLTAGE = 346.5        # V, target voltage during the PreCharge
MAX_VOLTAGE = 412.8            # V, target voltage during the CurrentDemand

# CCM_ChargeProgress, 0x5E9 B0 (bit 0 is an alive toggle)
PROG_PARAMS = 0x02             # charge parameters known
PROG_PRECHARGE = 0x0E
PROG_POWERDELIVERY = 0x1E
PROG_CURRENTDEMAND = 0x3E
PROG_ABORT_BIT = 0x40


def parse_profile(text):
    """'0:60,20:30' -> [(0.0, 60.0), (20.0, 30.0)], sorted by time."""
    return sorted((float(t), float(i)) for t, i in (item.split(":") for item in text.split(",")))


def profile_current(profile, t):
    """Target current of the profile at t seconds after the start of CurrentDemand."""
    current = profile[0][1]
    for t_point, i_point in profile:
        if t >= t_point:
            current = i_point
    return current


class Vehicle:
    def __init__(self, profile, log):
        self.profile = profile
        self.log = log
        self.toggle = False
        self.progress = 0
        self.params_known = False
        self.precharge_done = False
        self.power_delivery = False
        self.t_currentdemand = None
        self.current = 0.0           # A, target current in 0x59C
        self.evse_voltage = 0.0      # V, EVSE present voltage reported by the CCM in 0x5E5

    def on_ccm_progress(self, progress, t):
        if progress == self.progress:
            return
        self.progress = progress
        self.log(f"{t:8.3f}  CCM_ChargeProgress {progress >> 1}")
        if progress & PROG_ABORT_BIT:
            return
        if progress >= PROG_PARAMS:
            self.params_known = True
        if progress >= PROG_POWERDELIVERY:
            self.power_delivery = True
        if progress >= PROG_CURRENTDEMAND and self.t_currentdemand is None:
            self.t_currentdemand = t

    def on_cablecheck_done(self, t):
        """0x5E6 B1 bit 2: the CCM waits for a target current before it starts the PreCharge."""
        if self.current == 0.0 and self.t_currentdemand is None:
            self.current = 1.0
            self.log(f"{t:8.3f}  cable check done: request 1 A")

    def cycle(self, t):
        self.toggle = not self.toggle
        if (self.progress >= PROG_PRECHARGE and not self.precharge_done
                and self.evse_voltage >= BATTERY_VOLTAGE - 10.0):
            self.precharge_done = True
        if self.t_currentdemand is not None:
            target = profile_current(self.profile, t - self.t_currentdemand)
            if self.current < target:
                self.current = min(target, self.current + RAMP_A_PER_CYCLE)
            else:
                self.current = max(target, self.current - RAMP_A_PER_CYCLE)

    def frames(self):
        if self.current == 0.0:
            target_voltage = 0.0
        elif self.t_currentdemand is None:
            target_voltage = BATTERY_VOLTAGE
        else:
            target_voltage = MAX_VOLTAGE
        u = int(round(target_voltage * 10))
        i = int(round(self.current * 10))
        return {
            0x57F: [0x94, 0x76, 0x92, 0x00, 0x07, 0x20, 0x00, 0x05],
            0x597: [0x85 if self.toggle else 0x05, 0xC3, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x02 if self.power_delivery else 0x00],
            0x599: [0x09 if self.params_known else 0x08,
                    0x10 if self.precharge_done else 0x00,
                    0x44, 0xD0, 0x07, 0x20, 0x10,           # B2: SOC 34 %
                    0x03 if self.power_delivery else 0x01],  # B7 bit 0: CCS trigger
            0x5A3: [0x63, 0x30, 0x48, 0x00, 0x00, 0x00, 0x00, 0x00],
            0x59C: [0xBC, 0xA6, u & 0xFF, u >> 8, i & 0xFF, i >> 8, 0x60, 0x6D],
            0x59E: [0x64, 0x05, 0x48, 0x03, 0x89, 0x0D, 0x48, 0x26],  # 1380 s to full, 840 s to bulk, 98 kW
        }


def run(channel, duration, profile, log):
    vehicle = Vehicle(profile, log)
    last_5e5_log = 0.0
    with can.Bus(interface="pcan", channel=channel, bitrate=500000) as bus:
        log(f"Vehicle simulation on {channel} for {duration} s ...")
        t_start = time.monotonic()
        t_next = t_start
        while time.monotonic() - t_start < duration:
            now = time.monotonic()
            if now >= t_next:
                t_next += CYCLE_S
                vehicle.cycle(now - t_start)
                for can_id, data in vehicle.frames().items():
                    try:
                        bus.send(can.Message(arbitration_id=can_id, data=data, is_extended_id=False))
                    except can.CanError as e:
                        log(f"{now - t_start:8.3f}  send 0x{can_id:03X} failed: {e}")
            msg = bus.recv(timeout=max(0.0, t_next - time.monotonic()))
            if msg is None or msg.is_error_frame:
                continue
            t = time.monotonic() - t_start
            data = bytes(msg.data)
            if msg.arbitration_id == 0x5E9:
                vehicle.on_ccm_progress(data[0] & 0xFE, t)
            elif msg.arbitration_id == 0x5E6 and data[1] & 0x04 and not data[0] & 0x02:
                vehicle.on_cablecheck_done(t)
            elif msg.arbitration_id == 0x5E5:
                vehicle.evse_voltage = (data[4] | data[5] << 8) / 10
                if vehicle.t_currentdemand is not None and t - last_5e5_log >= 1.0:
                    last_5e5_log = t
                    log(f"{t:8.3f}  target current {vehicle.current:5.1f} A, "
                        f"EVSE {vehicle.evse_voltage:5.1f} V {(data[6] | data[7] << 8) / 10:5.1f} A")


def main():
    parser = argparse.ArgumentParser(description="Vehicle simulation for a CCS charging session with the Ioniq CCM")
    parser.add_argument("-c", "--channel", default="PCAN_USBBUS1", help="PCAN channel (default PCAN_USBBUS1)")
    parser.add_argument("-d", "--duration", type=float, default=90.0, help="run time in s (default 90)")
    parser.add_argument("--current", default="0:50",
                        help="target current profile t:A,t:A,... (t = s after the start of CurrentDemand, default 0:50)")
    parser.add_argument("-o", "--output", help="also write the log to this file")
    args = parser.parse_args()
    logfile = open(args.output, "w") if args.output else None

    def log(line):
        print(line, flush=True)
        if logfile:
            logfile.write(line + "\n")
            logfile.flush()

    run(args.channel, args.duration, parse_profile(args.current), log)


if __name__ == "__main__":
    main()
