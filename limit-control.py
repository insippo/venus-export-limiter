#!/usr/bin/env python3

import logging
import subprocess
import os
import sys
from config import MAX_MULTIPLUS_OUTPUT_W, PHASE_COUNT, MIN_OUTPUT_LIMIT_W, MAX_POWER_CHANGE_PER_STEP, GRADUAL_ADJUSTMENT
from dbus.mainloop.glib import DBusGMainLoop
import dbus

DBusGMainLoop(set_as_default=True)

log_path = "/data/dbus-limit/limit.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

# Validate configuration on startup
def validate_config():
    errors = []
    
    if not isinstance(MAX_MULTIPLUS_OUTPUT_W, (int, float)) or MAX_MULTIPLUS_OUTPUT_W <= 0:
        errors.append(f"MAX_MULTIPLUS_OUTPUT_W must be a positive number, got: {MAX_MULTIPLUS_OUTPUT_W}")
    
    if not isinstance(PHASE_COUNT, int) or PHASE_COUNT not in [1, 3]:
        errors.append(f"PHASE_COUNT must be 1 or 3, got: {PHASE_COUNT}")
    
    if not isinstance(MIN_OUTPUT_LIMIT_W, (int, float)) or MIN_OUTPUT_LIMIT_W < 0:
        errors.append(f"MIN_OUTPUT_LIMIT_W must be non-negative, got: {MIN_OUTPUT_LIMIT_W}")
    
    if MIN_OUTPUT_LIMIT_W >= MAX_MULTIPLUS_OUTPUT_W:
        errors.append(f"MIN_OUTPUT_LIMIT_W ({MIN_OUTPUT_LIMIT_W}) must be less than MAX_MULTIPLUS_OUTPUT_W ({MAX_MULTIPLUS_OUTPUT_W})")
    
    if errors:
        for error in errors:
            logging.error(f"Configuration error: {error}")
        sys.exit(1)
    
    logging.info(f"Configuration validated: MAX_MULTIPLUS_OUTPUT={MAX_MULTIPLUS_OUTPUT_W}W, PHASES={PHASE_COUNT}, MIN_OUTPUT={MIN_OUTPUT_LIMIT_W}W")

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

def get_multiplus_output_power():
    """Loeb Multiplus'te praegust väljundvõimsust"""
    # Try common VEBus device paths
    vebus_devices = [
        'com.victronenergy.vebus.ttyS4',
        'com.victronenergy.vebus.ttyO1', 
        'com.victronenergy.vebus.ttyUSB0',
        'com.victronenergy.vebus.can0'
    ]
    
    for device in vebus_devices:
        try:
            # Proovi lugeda AC väljundvõimsust
            iface = get_dbus_interface(device, '/Ac/Out/P')
            if iface:
                result = iface.GetValue()
                output_power = float(result)
                logging.info(f"Loetud Multiplus väljundvõimsus: {output_power} W (seade: {device})")
                return output_power, device
        except Exception:
            continue
    
    # Kui ei leia /Ac/Out/P, proovi alternatiivset teed
    for device in vebus_devices:
        try:
            # Proovi faasidepõhist lugemist
            total_power = 0
            phases_found = 0
            
            for phase in ['L1', 'L2', 'L3']:
                try:
                    iface = get_dbus_interface(device, f'/Ac/Out/{phase}/P')
                    if iface:
                        phase_power = float(iface.GetValue())
                        total_power += phase_power
                        phases_found += 1
                        logging.debug(f"Faas {phase}: {phase_power} W")
                except Exception:
                    continue
            
            if phases_found > 0:
                logging.info(f"Loetud Multiplus väljundvõimsus: {total_power} W ({phases_found} faasi, seade: {device})")
                return total_power, device
                
        except Exception:
            continue
    
    logging.error("Ei leidnud ühtegi töötavat Multiplus seadet")
    return None, None

def set_multiplus_power_limit(limit_watts, vebus_device=None):
    """
    Seab Multiplus'te väljundvõimsuse piirangu.
    Kasutab otse Python DBus teeki kiiruse huvides.
    """
    global last_limit
    
    # Järkjärguline muutus, et vältida äkilisi hüppeid (kui lubatud)
    if GRADUAL_ADJUSTMENT and last_limit is not None:
        if abs(limit_watts - last_limit) > MAX_POWER_CHANGE_PER_STEP:
            if limit_watts > last_limit:
                limit_watts = last_limit + MAX_POWER_CHANGE_PER_STEP
            else:
                limit_watts = last_limit - MAX_POWER_CHANGE_PER_STEP
            logging.info(f"Järkjärguline muutus: {last_limit} -> {limit_watts} W (samm: {MAX_POWER_CHANGE_PER_STEP}W)")
    
    # Salvesta viimane piirang
    last_limit = limit_watts
    
    # Kui ei ole antud konkreetset seadet, proovi leida
    if not vebus_device:
        vebus_devices = [
            'com.victronenergy.vebus.ttyS4',
            'com.victronenergy.vebus.ttyO1', 
            'com.victronenergy.vebus.ttyUSB0',
            'com.victronenergy.vebus.can0'
        ]
    else:
        vebus_devices = [vebus_device]
    
        for device in vebus_devices:
        success = False
        
        try:
            # Meetod 1: Otsene AC väljundvõimsuse piirang
            power_limit_paths = [
                '/Ac/PowerLimit',
                '/Ac/Out/PowerLimit',
                '/Settings/PowerLimit'
            ]
            
            for path in power_limit_paths:
                try:
                    iface = get_dbus_interface(device, path)
                    if iface:
                        iface.SetValue(dbus.Int32(int(limit_watts)))
                        logging.info(f"Multiplus {device} {path} seatud: {limit_watts} W")
                        success = True
                        break
                except Exception:
                    continue
            
            if success:
                return
            
            # Meetod 2: Faasipõhine piirang
            if PHASE_COUNT == 3:
                per_phase_limit = int(limit_watts / 3)
                phases_set = 0
                
                for phase in ['L1', 'L2', 'L3']:
                    phase_paths = [
                        f'/Ac/Out/{phase}/PowerLimit',
                        f'/Ac/{phase}/PowerLimit'
                    ]
                    
                    for path in phase_paths:
                        try:
                            iface = get_dbus_interface(device, path)
                            if iface:
                                iface.SetValue(dbus.Int32(per_phase_limit))
                                logging.info(f"Multiplus {device} {path} seatud: {per_phase_limit} W")
                                phases_set += 1
                                break
                        except Exception:
                            continue
                
                if phases_set >= 2:  # Kui vähemalt 2 faasi õnnestus
                    logging.info(f"Faasipõhine piirang seatud: {phases_set}/3 faasi")
                    return
            
            # Meetod 3: VE.Bus MaxPower seade
            try:
                iface = get_dbus_interface(device, '/Settings/MaxPower')
                if iface:
                    iface.SetValue(dbus.Int32(int(limit_watts)))
                    logging.info(f"Multiplus {device} MaxPower seatud: {limit_watts} W")
                    return
            except Exception:
                pass
                
            # Meetod 4: Kui on ESS režiim, kasuta Hub4 seadeid
            try:
                # Kontrolli, kas Hub4 on aktiivne
                hub4_iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/Hub4Mode')
                if hub4_iface and int(hub4_iface.GetValue()) == 3:
                    # Kasuta ESS piiranguid
                    ess_iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/MaxDischargePower')
                    if ess_iface:
                        ess_iface.SetValue(dbus.Int32(int(limit_watts)))
                        logging.info(f"ESS MaxDischargePower seatud: {limit_watts} W")
                        return
            except Exception:
                pass
                
        except Exception as e:
            logging.warning(f"Seadme {device} seadmine ebaõnnestus: {e}")
            continue
    
    logging.error("Kõik Multiplus piirangu meetodid ebaõnnestusid")



def main():
    logging.info("Multiplus väljundvõimsuse piirangu skript käivitus.")
    
    # Loe Multiplus'te praegust väljundvõimsust
    output_power, vebus_device = get_multiplus_output_power()
    if output_power is None:
        logging.warning("Multiplus väljundvõimsus puudub, katkestan.")
        return

    logging.info(f"Praegune Multiplus väljundvõimsus: {output_power} W")
    
    # Kontrolli, kas väljundvõimsus ületab lubatud piiri
    if output_power <= MAX_MULTIPLUS_OUTPUT_W:
        logging.info(f"Väljundvõimsus {output_power} W on lubatud piiri {MAX_MULTIPLUS_OUTPUT_W} W sees - piiranguid pole vaja.")
        # Eemalda võimalikud varasemad piirangud, seades maksimaalse lubatud võimsuse
        set_multiplus_power_limit(MAX_MULTIPLUS_OUTPUT_W, vebus_device)
        return
    
    # Väljundvõimsus ületab piiri - rakenda piirang
    logging.warning(f"Väljundvõimsus {output_power} W ületab piiri {MAX_MULTIPLUS_OUTPUT_W} W!")
    
    # Arvuta uus piirang (väikese reserviga, et vältida kõikumist)
    new_limit = MAX_MULTIPLUS_OUTPUT_W - 500  # 500W reserv
    
    if new_limit < MIN_OUTPUT_LIMIT_W:
        new_limit = MIN_OUTPUT_LIMIT_W
        logging.warning(f"Arvutatud piirang {new_limit} W on alla miinimumi, kasutan miinimumi: {MIN_OUTPUT_LIMIT_W} W")

    logging.info(f"Seatan Multiplus väljundpiirangu: {new_limit} W")
    set_multiplus_power_limit(new_limit, vebus_device)

if __name__ == "__main__":
    main()
