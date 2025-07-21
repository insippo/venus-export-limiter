#!/usr/bin/env python3
import dbus
import time

LIMIT = 15000  # maksimaalne eksport W
BUS = dbus.SystemBus()

def get_power(path):
    try:
        obj = BUS.get_object('com.victronenergy.pvinverter.pvinverter0', path) if 'pvinverter' in path else BUS.get_object('com.victronenergy.vebus.ttyO1', path)
        iface = dbus.Interface(obj, 'com.victronenergy.BusItem')
        return float(iface.GetValue())
    except Exception:
        return 0

def get_export_limit():
    """Reads current AC Power SetPoint from the com.victronenergy.settings service"""
    try:
        obj = BUS.get_object('com.victronenergy.settings', '/Settings/CGwacs/AcPowerSetPoint')
        iface = dbus.Interface(obj, 'com.victronenergy.BusItem')
        value = iface.GetValue()
        return int(value) if value is not None else None
    except Exception:
        return None

def set_export_limit(value):
    try:
        obj = BUS.get_object('com.victronenergy.settings', '/Settings/CGwacs/AcPowerSetPoint')
        iface = dbus.Interface(obj, 'com.victronenergy.BusItem')
        iface.SetValue(int(value))
    except Exception:
        pass

while True:
    pv = get_power('/Ac/Power')
    multi = get_power('/Ac/Out/P')
    total = pv + multi

    if total > LIMIT:
        new_limit = int((total - LIMIT) * -1)
    else:
        new_limit = 0

    set_export_limit(new_limit)
    time.sleep(2)
