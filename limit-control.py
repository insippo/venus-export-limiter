#!/usr/bin/env python3

import logging
import subprocess
import os
import sys
from config import MAX_EXPORT_LIMIT_W, PHASE_COUNT, MIN_OUTPUT_LIMIT_W, MAX_POWER_CHANGE_PER_STEP, GRADUAL_ADJUSTMENT
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

# Globaalne muutuja viimase piirangu jälgimiseks
last_limit = None

def get_current_ess_limit():
    """Loeb praeguse ESS piirangu"""
    try:
        cmd = [
            "dbus-send", "--system", "--print-reply",
            "--dest=com.victronenergy.settings",
            "/Settings/CGwacs/AcPowerSetPoint",
            "com.victronenergy.BusItem.GetValue"
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # Parse DBus vastust
        for line in result.stdout.split('\n'):
            if 'int32' in line:
                value = int(line.split()[-1])
                return value
        return None
    except Exception as e:
        logging.debug(f"Ei saanud praegust ESS piirangut lugeda: {e}")
        return None

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

def set_vebus_output_limit(limit_watts):
    """
    Seab Multiplus väljundpiirangu kasutades ESS seadeid.
    Negatiivne väärtus = laadimispiirang, positiivne = tühjendusp piirang
    """
    global last_limit
    
    # Järkjärguline muutus, et vältida äkilisi hüppeid (kui lubatud)
    if GRADUAL_ADJUSTMENT:
        current_limit = get_current_ess_limit()
        if current_limit is not None and last_limit is not None:
            if abs(limit_watts - current_limit) > MAX_POWER_CHANGE_PER_STEP:
                if limit_watts > current_limit:
                    limit_watts = current_limit + MAX_POWER_CHANGE_PER_STEP
                else:
                    limit_watts = current_limit - MAX_POWER_CHANGE_PER_STEP
                logging.info(f"Järkjärguline muutus: {current_limit} -> {limit_watts} W (samm: {MAX_POWER_CHANGE_PER_STEP}W)")
    
    # Salvesta viimane piirang
    last_limit = limit_watts
    
    try:
        # Kasuta ESS seadeid, mitte otse VEBus käske
        # AcPowerSetPoint määrab maksimaalse AC väljundvõimsuse
        cmd = [
            "dbus-send", "--system", "--print-reply",
            "--dest=com.victronenergy.settings",
            "/Settings/CGwacs/AcPowerSetPoint",
            "com.victronenergy.BusItem.SetValue",
            f"variant:int32:{int(limit_watts)}"
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"ESS AcPowerSetPoint seatud: {limit_watts} W")
        logging.debug(f"DBus vastus: {result.stdout.strip()}")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"DBus käsk ebaõnnestus: {e}")
        logging.error(f"Stderr: {e.stderr}")
        
        # Proovi alternatiivset meetodit - Hub4 režiimi seadeid
        try:
            logging.info("Proovin alternatiivset Hub4 meetodit...")
            cmd_alt = [
                "dbus-send", "--system", "--print-reply",
                "--dest=com.victronenergy.settings", 
                "/Settings/CGwacs/Hub4Mode",
                "com.victronenergy.BusItem.SetValue",
                "variant:int32:3"  # Hub4 režiim sisse
            ]
            subprocess.run(cmd_alt, check=True)
            
            # Seejärel sea võimsuspiirang
            cmd_power = [
                "dbus-send", "--system", "--print-reply",
                "--dest=com.victronenergy.settings",
                "/Settings/CGwacs/MaxDischargePower", 
                "com.victronenergy.BusItem.SetValue",
                f"variant:int32:{int(limit_watts)}"
            ]
            subprocess.run(cmd_power, check=True)
            logging.info(f"Hub4 MaxDischargePower seatud: {limit_watts} W")
            
        except Exception as e2:
            logging.error(f"Ka alternatiivne meetod ebaõnnestus: {e2}")
    
    except Exception as e:
        logging.error(f"Üldine viga väljundvõimsuse seadmisel: {e}")

def check_ess_configuration():
    """Kontrollib, et ESS on õigesti konfigureeritud"""
    try:
        # Kontrolli, et Hub4 režiim on sisse lülitatud
        cmd = [
            "dbus-send", "--system", "--print-reply",
            "--dest=com.victronenergy.settings",
            "/Settings/CGwacs/Hub4Mode",
            "com.victronenergy.BusItem.GetValue"
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        hub4_mode = None
        for line in result.stdout.split('\n'):
            if 'int32' in line:
                hub4_mode = int(line.split()[-1])
                break
        
        if hub4_mode != 3:
            logging.warning(f"Hub4 režiim pole õigesti seadistatud (praegu: {hub4_mode}, peaks olema: 3)")
            # Proovi automaatselt sisse lülitada
            cmd_set = [
                "dbus-send", "--system", "--print-reply",
                "--dest=com.victronenergy.settings",
                "/Settings/CGwacs/Hub4Mode", 
                "com.victronenergy.BusItem.SetValue",
                "variant:int32:3"
            ]
            subprocess.run(cmd_set, check=True)
            logging.info("Hub4 režiim sisse lülitatud")
        
        return True
        
    except Exception as e:
        logging.error(f"ESS konfiguratsiooni kontroll ebaõnnestus: {e}")
        return False

def main():
    logging.info("Skript käivitus.")
    
    # Kontrolli ESS konfiguratsiooni
    if not check_ess_configuration():
        logging.error("ESS pole õigesti konfigureeritud, katkestan.")
        return
    
    exported_power = get_export_power()
    if exported_power is None:
        logging.warning("Eksportvõimsus puudub, katkestan.")
        return

    # Only limit when actually exporting power (positive values)
    # Negative values mean importing from grid, no limiting needed
    if exported_power <= 0:
        logging.info(f"Importimine võrgust: {exported_power} W, piiranguid ei rakenda.")
        # Set maximum allowed output when importing
        set_vebus_output_limit(MAX_EXPORT_LIMIT_W)
        return
    
    export = exported_power
    allowed_output = MAX_EXPORT_LIMIT_W - export

    if allowed_output < MIN_OUTPUT_LIMIT_W:
        allowed_output = MIN_OUTPUT_LIMIT_W
        logging.warning(f"Eksport {export} W ületab piiri, seatan miinimumi: {allowed_output} W")

    logging.info(f"Eksport: {export} W, lubatud väljund: {allowed_output} W")
    set_vebus_output_limit(allowed_output)

if __name__ == "__main__":
    main()
