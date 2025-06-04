#!/usr/bin/env python3

import logging
import subprocess
import os
from config import MAX_EXPORT_LIMIT_W, PHASE_COUNT, MIN_OUTPUT_LIMIT_W
from dbus.mainloop.glib import DBusGMainLoop
import dbus

DBusGMainLoop(set_as_default=True)

log_path = "/data/dbus-limit/limit.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

def get_export_power():
    bus = dbus.SystemBus()
    try:
        obj = bus.get_object('com.victronenergy.grid.INSERT-YOUR-DEVICE-HERE', '/Ac/Power')
        iface = dbus.Interface(obj, dbus_interface='com.victronenergy.BusItem')
        result = iface.GetValue()
        exported_power = float(result)
        logging.info(f"Loetud eksportvõimsus: {exported_power} W")
        return exported_power
    except Exception as e:
        logging.error(f"Viga eksportvõimsuse lugemisel: {e}")
        return None

def set_vebus_output_limit(limit_per_phase):
    total_limit = limit_per_phase * PHASE_COUNT
    try:
        cmd = [
            "dbus-send", "--system",
            "--dest=com.victronenergy.vebus.ttyS4",
            "/Hub4",
            "com.victronenergy.BusItem.SetValue",
            "string:/AcPowerSetpoint",
            f"double:{total_limit:.1f}"
        ]
        subprocess.run(cmd, check=True)
        logging.info(f"Seatud väljund: {total_limit} W (ehk {limit_per_phase} W/faas)")
    except Exception as e:
        logging.error(f"Viga väljundvõimsuse seadmisel: {e}")

def main():
    logging.info("Skript käivitus.")
    exported_power = get_export_power()
    if exported_power is None:
        logging.warning("Eksportvõimsus puudub, katkestan.")
        return

    export = max(exported_power, 0)
    allowed_output = MAX_EXPORT_LIMIT_W - export

    if allowed_output < MIN_OUTPUT_LIMIT_W:
        allowed_output = MIN_OUTPUT_LIMIT_W

    limit_per_phase = int(allowed_output / PHASE_COUNT)
    set_vebus_output_limit(limit_per_phase)

if __name__ == "__main__":
    main()
