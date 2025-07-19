# Venus Export Limiter v2.0 (Minimal)

## Purpose

Limit grid export on Victron Venus OS systems by dynamically adjusting `AcPowerSetPoint`, using only D-Bus calls. No logging, no file writes.

## Features

- Reads inverter and MultiPlus export power
- Calculates total export and limits to max (default 15 kW)
- Sets D-Bus path `/Settings/CGwacs/AcPowerSetPoint` accordingly
- Extremely lightweight and memory-safe

## Paths used

- PV: `/Ac/Power` on `com.victronenergy.pvinverter.pvinverter0`
- MultiPlus: `/Ac/Out/P` on `com.victronenergy.vebus.ttyO1`
- Export limit: `/Settings/CGwacs/AcPowerSetPoint`

## Systemd install

1. Clone repo to `/data/venus-export-limiter-v2`
2. Copy `.service` file to `/etc/systemd/system/`
3. Enable & start:

```bash
systemctl daemon-reexec
systemctl enable venus-limiter-v2
systemctl start venus-limiter-v2
```

## License

MIT
# Venus Export Limiter v2.0 – Minimal

See versioon piirab võrku eksporditavat võimsust otse D-Bus kaudu, ilma logimiseta ja ilma mälukasutust suurendamata. Sobib Cerbo GX seadmetele, kus süsteem peab töötama kergelt ja katkestusteta.

## Omadused

- Otsepöördus D-Bus'ile (ei kasuta DBusMonitori ega logifaile)
- Piirab eksporti näiteks 15 000 W peale (muudetav)
- Arvestab korraga PV inverterit ja MultiPlus väljundit
- Jookseb loopina iga 2 sekundi järel
- Ei jäta jälgi ega logisid

## Kasutatavad D-Bus aadressid

- PV: `com.victronenergy.pvinverter.pvinverter0 /Ac/Power`
- MultiPlus: `com.victronenergy.vebus.ttyO1 /Ac/Out/P`
- Piirangu seadmine: `com.victronenergy.settings /Settings/CGwacs/AcPowerSetPoint`

## Paigaldamine

1. Kopeeri skript ja teenusefail Cerbo GX seadmesse:
   ```bash
   mkdir -p /data/venus-export-limiter-v2
   cp limit-control-v2.py /data/venus-export-limiter-v2/
   cp venus-limiter-v2.service /etc/systemd/system/

systemctl daemon-reexec
systemctl enable venus-limiter-v2
systemctl start venus-limiter-v2

systemctl status venus-limiter-v2


Muudatused võrreldes v1-ga
Eemaldatud logimine ja kõik tarbetud funktsioonid

Oluliselt kiirem ja stabiilsem

Mõeldud jooksma ilma katkestusteta Cerbo GX sisemälus

Litsents
MIT
