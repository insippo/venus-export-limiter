#!/usr/bin/env python3

import logging
import subprocess
import os
import sys
from config import MAX_EXPORT_LIMIT_W, PHASE_COUNT, MIN_OUTPUT_LIMIT_W
from dbus.mainloop.glib import DBusGMainLoop
import dbus

DBusGMainLoop(set_as_default=True)

log_path = "/data/dbus-limit/limit.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

# Validate configuration on startup
def validate_config():
    errors = []
    
    if not isinstance(MAX_EXPORT_LIMIT_W, (int, float)) or MAX_EXPORT_LIMIT_W <= 0:
        errors.append(f"MAX_EXPORT_LIMIT_W must be a positive number, got: {MAX_EXPORT_LIMIT_W}")
    
    if not isinstance(PHASE_COUNT, int) or PHASE_COUNT not in [1, 3]:
        errors.append(f"PHASE_COUNT must be 1 or 3, got: {PHASE_COUNT}")
    
    if not isinstance(MIN_OUTPUT_LIMIT_W, (int, float)) or MIN_OUTPUT_LIMIT_W < 0:
        errors.append(f"MIN_OUTPUT_LIMIT_W must be non-negative, got: {MIN_OUTPUT_LIMIT_W}")
    
    if MIN_OUTPUT_LIMIT_W >= MAX_EXPORT_LIMIT_W:
        errors.append(f"MIN_OUTPUT_LIMIT_W ({MIN_OUTPUT_LIMIT_W}) must be less than MAX_EXPORT_LIMIT_W ({MAX_EXPORT_LIMIT_W})")
    
    if errors:
        for error in errors:
            logging.error(f"Configuration error: {error}")
        sys.exit(1)
    
    logging.info(f"Configuration validated: MAX_EXPORT={MAX_EXPORT_LIMIT_W}W, PHASES={PHASE_COUNT}, MIN_OUTPUT={MIN_OUTPUT_LIMIT_W}W")

validate_config()

def get_export_power():
    bus = dbus.SystemBus()
    
    # Try common grid meter device paths
    grid_devices = [
        'com.victronenergy.grid.cgwacs_ttyUSB0_di30_mb1',
        'com.victronenergy.grid.ttyUSB0',
        'com.victronenergy.grid.ttyUSB1', 
        'com.victronenergy.grid.ttyS4',
        'com.victronenergy.grid.cgwacs_ttyS4_di30_mb1'
    ]
    
    for device in grid_devices:
        try:
            obj = bus.get_object(device, '/Ac/Power')
            iface = dbus.Interface(obj, dbus_interface='com.victronenergy.BusItem')
            result = iface.GetValue()
            exported_power = float(result)
            logging.info(f"Loetud eksportvõimsus: {exported_power} W (seade: {device})")
            return exported_power
        except Exception:
            continue
    
    logging.error("Ei leidnud ühtegi töötavat grid seadet")
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

    # Only limit when actually exporting power (positive values)
    # Negative values mean importing from grid, no limiting needed
    if exported_power <= 0:
        logging.info(f"Importimine võrgust: {exported_power} W, piiranguid ei rakenda.")
        # Set maximum allowed output when importing
        limit_per_phase = int(MAX_EXPORT_LIMIT_W / PHASE_COUNT)
        set_vebus_output_limit(limit_per_phase)
        return
    
    export = exported_power
    allowed_output = MAX_EXPORT_LIMIT_W - export

    if allowed_output < MIN_OUTPUT_LIMIT_W:
        allowed_output = MIN_OUTPUT_LIMIT_W
        logging.warning(f"Eksport {export} W ületab piiri, seatan miinimumi: {allowed_output} W")

    limit_per_phase = int(allowed_output / PHASE_COUNT)
    logging.info(f"Eksport: {export} W, lubatud väljund: {allowed_output} W")
    set_vebus_output_limit(limit_per_phase)

if __name__ == "__main__":
    main()
