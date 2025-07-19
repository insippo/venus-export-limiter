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

# Globaalsed muutujad
last_limit = None
system_bus = None
dbus_objects_cache = {}

def get_system_bus():
    """Tagastab püsiva DBus ühenduse"""
    global system_bus
    if system_bus is None:
        system_bus = dbus.SystemBus()
    return system_bus

def get_dbus_interface(service, path, interface='com.victronenergy.BusItem'):
    """Tagastab cache'itud DBus liidese"""
    global dbus_objects_cache
    cache_key = f"{service}:{path}:{interface}"
    
    if cache_key not in dbus_objects_cache:
        try:
            bus = get_system_bus()
            obj = bus.get_object(service, path)
            iface = dbus.Interface(obj, dbus_interface=interface)
            dbus_objects_cache[cache_key] = iface
        except Exception as e:
            logging.debug(f"DBus liidese loomine ebaõnnestus {cache_key}: {e}")
            return None
    
    return dbus_objects_cache.get(cache_key)

def get_current_ess_limit():
    """Loeb praeguse ESS piirangu kasutades cache'itud DBus liidest"""
    try:
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/AcPowerSetPoint')
        if iface:
            value = int(iface.GetValue())
            return value
        return None
    except Exception as e:
        logging.debug(f"Ei saanud praegust ESS piirangut lugeda: {e}")
        return None

def get_export_power():
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
            iface = get_dbus_interface(device, '/Ac/Power')
            if iface:
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
    Kasutab otse Python DBus teeki kiiruse huvides.
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
    
    bus = get_system_bus()
    
    try:
        # Esimene meetod: AcPowerSetPoint (põhiline ESS seade)
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/AcPowerSetPoint')
        if iface:
            iface.SetValue(dbus.Int32(int(limit_watts)))
            logging.info(f"ESS AcPowerSetPoint seatud: {limit_watts} W")
            return
        
    except Exception as e:
        logging.warning(f"AcPowerSetPoint seadmine ebaõnnestus: {e}")
    
    # Teine meetod: MaxDischargePower
    try:
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/MaxDischargePower')
        if iface:
            iface.SetValue(dbus.Int32(int(limit_watts)))
            logging.info(f"ESS MaxDischargePower seatud: {limit_watts} W")
            return
            
            except Exception as e2:
        logging.warning(f"MaxDischargePower seadmine ebaõnnestus: {e2}")
    
    # Kolmas meetod: otsene VEBus käsk (ettevaatlik!)
    try:
        # Leia VEBus seade
        vebus_devices = [
            'com.victronenergy.vebus.ttyS4',
            'com.victronenergy.vebus.ttyO1', 
            'com.victronenergy.vebus.ttyUSB0'
        ]
        
        for device in vebus_devices:
            try:
                # Proovi erinevaid VEBus teid
                vebus_paths = [
                    '/Hub4/L1/AcPowerSetpoint',
                    '/Ac/PowerLimit',
                    '/Hub4/DisableFeedIn'
                ]
                
                for path in vebus_paths:
                    try:
                        iface = get_dbus_interface(device, path)
                        if iface:
                            if 'AcPowerSetpoint' in path:
                                # Jaga faasideks
                                per_phase = int(limit_watts / PHASE_COUNT)
                                iface.SetValue(dbus.Double(float(per_phase)))
                                logging.info(f"VEBus {device} {path} seatud: {per_phase} W")
                                
                                if PHASE_COUNT == 3:
                                    # Sama ka teistele faasidele
                                    for phase in ['L2', 'L3']:
                                        phase_path = path.replace('L1', phase)
                                        iface_phase = get_dbus_interface(device, phase_path)
                                        if iface_phase:
                                            iface_phase.SetValue(dbus.Double(float(per_phase)))
                                            logging.info(f"VEBus {device} {phase_path} seatud: {per_phase} W")
                                
                            elif 'PowerLimit' in path:
                                iface.SetValue(dbus.Int32(int(limit_watts)))
                                logging.info(f"VEBus {device} PowerLimit seatud: {limit_watts} W")
                            
                            return
                    except Exception:
                        continue
                        
            except Exception:
                continue
        
        logging.error("Kõik meetodid ebaõnnestusid - ei saanud võimsuspiirangut seada")
        
    except Exception as e3:
        logging.error(f"VEBus otsene käsk ebaõnnestus: {e3}")

def check_ess_configuration():
    """Kontrollib, et ESS on õigesti konfigureeritud kasutades cache'itud DBus liidest"""
    try:
        # Kontrolli, et Hub4 režiim on sisse lülitatud
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/Hub4Mode')
        if not iface:
            logging.error("Ei saanud Hub4Mode liidest")
            return False
            
        hub4_mode = int(iface.GetValue())
        
        if hub4_mode != 3:
            logging.warning(f"Hub4 režiim pole õigesti seadistatud (praegu: {hub4_mode}, peaks olema: 3)")
            # Proovi automaatselt sisse lülitada
            iface.SetValue(dbus.Int32(3))
            logging.info("Hub4 režiim sisse lülitatud")
        else:
            logging.info("Hub4 režiim on õigesti konfigureeritud")
        
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
