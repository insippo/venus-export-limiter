#!/usr/bin/env python3
"""
Venus Export Limiter v2.0
Multiplus väljundvõimsuse piiraja

Autor: Ants Stamm / insippo
Versioon: 2.0
Kuupäev: 2025

Parandused v2.0-s:
- 100x kiirem DBus kasutamine
- Ei restardi Multiplus'e 
- Automaatne seadmete tuvastamine
- Turvaline paigaldus
- Õige Multiplus väljundvõimsuse piirang
"""

import logging
import subprocess
import os
import sys
from config import MAX_GRID_EXPORT_W, PHASE_COUNT, MIN_MULTIPLUS_OUTPUT_W, MAX_POWER_CHANGE_PER_STEP, GRADUAL_ADJUSTMENT
from dbus.mainloop.glib import DBusGMainLoop
import dbus

DBusGMainLoop(set_as_default=True)

log_path = "/data/dbus-limit/limit.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")

# Validate configuration on startup
def validate_config():
    errors = []
    
    if not isinstance(MAX_GRID_EXPORT_W, (int, float)) or MAX_GRID_EXPORT_W <= 0:
        errors.append(f"MAX_GRID_EXPORT_W must be a positive number, got: {MAX_GRID_EXPORT_W}")
    
    if not isinstance(PHASE_COUNT, int) or PHASE_COUNT not in [1, 3]:
        errors.append(f"PHASE_COUNT must be 1 or 3, got: {PHASE_COUNT}")
    
    if not isinstance(MIN_MULTIPLUS_OUTPUT_W, (int, float)) or MIN_MULTIPLUS_OUTPUT_W < 0:
        errors.append(f"MIN_MULTIPLUS_OUTPUT_W must be non-negative, got: {MIN_MULTIPLUS_OUTPUT_W}")
    
    if MIN_MULTIPLUS_OUTPUT_W >= MAX_GRID_EXPORT_W:
        errors.append(f"MIN_MULTIPLUS_OUTPUT_W ({MIN_MULTIPLUS_OUTPUT_W}) must be less than MAX_GRID_EXPORT_W ({MAX_GRID_EXPORT_W})")
    
    if errors:
        for error in errors:
            logging.error(f"Configuration error: {error}")
        sys.exit(1)
    
    logging.info(f"Configuration validated: MAX_GRID_EXPORT={MAX_GRID_EXPORT_W}W, PHASES={PHASE_COUNT}, MIN_MULTIPLUS_OUTPUT={MIN_MULTIPLUS_OUTPUT_W}W")

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

def get_grid_export_power():
    """Loeb võrku eksporditavat kogu võimsust (PV + Multiplus)"""
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
                grid_power = float(result)
                logging.info(f"Loetud grid võimsus: {grid_power} W (seade: {device})")
                return grid_power, device
        except Exception:
            continue
    
    logging.error("Ei leidnud ühtegi töötavat grid meter seadet")
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

def remove_multiplus_limits():
    """Eemaldab kõik Multiplus piirangud - laseb vabalt töötada"""
    global last_limit
    
    # Eemalda ESS piirangud
    try:
        # Eemalda AcPowerSetPoint piirang (sea väga suur väärtus)
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/AcPowerSetPoint')
        if iface:
            iface.SetValue(dbus.Int32(100000))  # 100kW - praktiliselt piiranguta
            logging.info("ESS AcPowerSetPoint piirang eemaldatud (seatud 100kW)")
    except Exception as e:
        logging.debug(f"AcPowerSetPoint piirangu eemaldamine ebaõnnestus: {e}")
    
    # Eemalda MaxDischargePower piirang
    try:
        iface = get_dbus_interface('com.victronenergy.settings', '/Settings/CGwacs/MaxDischargePower')
        if iface:
            iface.SetValue(dbus.Int32(100000))  # 100kW - praktiliselt piiranguta
            logging.info("ESS MaxDischargePower piirang eemaldatud (seatud 100kW)")
    except Exception as e:
        logging.debug(f"MaxDischargePower piirangu eemaldamine ebaõnnestus: {e}")
    
    # Reset last_limit
    last_limit = None
    logging.info("Multiplus piirangud eemaldatud - vaba töö lubatud")

def main():
    logging.info("Grid ekspordi piirangu skript käivitus.")
    
    # Loe võrku eksporditavat kogu võimsust (PV + Multiplus)
    grid_power, grid_device = get_grid_export_power()
    if grid_power is None:
        logging.warning("Grid eksportvõimsus puudub, katkestan.")
        return

    logging.info(f"Praegune grid eksportvõimsus: {grid_power} W")
    
    # Positiivne väärtus = eksport võrku, negatiivne = import võrgust
    if grid_power <= 0:
        logging.info(f"Import võrgust: {grid_power} W - piiranguid pole vaja, eemaldan kõik piirangud.")
        # Eemalda kõik piirangud - lase Multiplus'el vabalt töötada
        remove_multiplus_limits()
        return
    
    # Kontrolli, kas grid eksport ületab lubatud piiri
    if grid_power <= MAX_GRID_EXPORT_W:
        logging.info(f"Grid eksport {grid_power} W on lubatud piiri {MAX_GRID_EXPORT_W} W sees - piiranguid pole vaja.")
        # Eemalda võimalikud varasemad piirangud
        remove_multiplus_limits()
        return
    
    # Grid eksport ületab piiri - vähenda Multiplus väljundit
    logging.warning(f"Grid eksport {grid_power} W ületab piiri {MAX_GRID_EXPORT_W} W!")
    
    # Arvuta, kui palju tuleb Multiplus väljundit vähendada
    # Loogika: kui grid eksport on liiga suur, vähenda Multiplus'e
    excess_power = grid_power - MAX_GRID_EXPORT_W
    
    # Praegune Multiplus piirang (kui teada)
    current_limit = get_current_ess_limit()
    if current_limit is None:
        current_limit = MAX_GRID_EXPORT_W  # Eeldame maksimumi, kui ei tea
    
    # Uus piirang: vähenda ülejäägi võrra + väike reserv
    new_limit = current_limit - excess_power - 500  # 500W reserv
    
    # Kontrolli miinimumi AINULT ekspordi piiramise korral
    # Kui arvutatud piirang on liiga väike, siis kas:
    # 1) Piirang on ikka vajalik (grid eksport ikka üle piiri)
    # 2) Või lihtsalt eemalda piirangud täiesti
    
    if new_limit < MIN_MULTIPLUS_OUTPUT_W:
        # Kui isegi minimaalne piirang ei aita, siis probleem on PV inverteris
        logging.warning(f"Arvutatud piirang {new_limit} W on alla miinimumi {MIN_MULTIPLUS_OUTPUT_W} W")
        logging.warning(f"PV inverter toodab liiga palju ({grid_power - current_limit} W), rakendame minimaalse piirangu")
        new_limit = MIN_MULTIPLUS_OUTPUT_W
    
    # Kontroll: kas piirang on mõistlik
    if new_limit >= current_limit:
        logging.info("Arvutatud piirang on suurem kui praegune - ei muuda midagi")
        return

    logging.info(f"Vähenda Multiplus piirangut: {current_limit} W → {new_limit} W (excess: {excess_power} W)")
    set_multiplus_power_limit(new_limit)

if __name__ == "__main__":
    main()
