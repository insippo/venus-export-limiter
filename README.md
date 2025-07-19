# Venus Export Limiter v2.0

[![GitHub Repo](https://img.shields.io/badge/GitHub-insippo%2Fvenus--export--limiter-blue?logo=github)](https://github.com/insippo/venus-export-limiter)
[![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python)](https://www.python.org/)
[![Systemd](https://img.shields.io/badge/Systemd-supported-blue?logo=linux)](https://www.freedesktop.org/wiki/Software/systemd/)
[![Platform](https://img.shields.io/badge/Venus--OS-tested-brightgreen?logo=raspberry-pi)](https://www.victronenergy.com/live/venus-os:start)
[![Version](https://img.shields.io/badge/Version-2.0-success)](https://github.com/insippo/venus-export-limiter/tree/v2)

## 🆕 v2.0 Uuendused

- ✅ **100x kiirem** - otsene Python DBus kasutamine
- ✅ **Ei restardi Multiplus'e** - järkjärguline võimsuse muutus
- ✅ **Automaatne seadmete tuvastamine** - ei vaja käsitsi konfigureerimist
- ✅ **Turvaline paigaldus** - commit hash verification
- ✅ **Õige funktsionaalsus** - piirab Multiplus väljundit, mitte grid eksporti
- ✅ **DBus cache** - optimeeritud jõudlus

## ℹ️ Ülevaade

See projekt piirab Victron Venus OS-is Multiplus'te väljundvõimsust, et see ei ületaks määratud piiri.  
Kui Multiplus'te väljundvõimsus ületab `MAX_MULTIPLUS_OUTPUT_W` (30kW), siis skript rakendab võimsuspiirangu.

## ⚠️ HOIATUS

**Kui kasutad seda valesti või vales seadmes, võib see rikkuda Venus OS-i töö. Ära paigalda seda süsteemi, millest sa aru ei saa.**  
Skripti võib täiesti valesti seadistatuna kasutada nagu "lunarahaviirust", mis katkestab energiavoogu või piirab Multiplus väljundit nulli.

**KASUTA OMAL VASTUTUSEL.**

## 🚀 Kiire automaatne paigaldus

```bash
wget https://raw.githubusercontent.com/insippo/venus-export-limiter/master/install.sh
bash install.sh
```

See kloonib repo `/data/dbus-limit` alla, seab õigused, paigaldab systemd teenuse ja käivitab selle.

## ⚙️ Käsitsi seadistamine

Muuda `config.py` vastavalt oma süsteemile:

```python
MAX_MULTIPLUS_OUTPUT_W = 30000      # Maksimaalne Multiplus väljundvõimsus (W)
PHASE_COUNT = 3
MIN_OUTPUT_LIMIT_W = 1000
```

Skript leiab Multiplus seadmed automaatselt.

## 🔁 Systemd teenus

```bash
cp systemd/venus-export-limiter.service /etc/systemd/system/
systemctl daemon-reexec
systemctl enable --now venus-export-limiter.service
```

## 📄 Logid

```bash
tail -f /data/dbus-limit/limit.log
```

## ✅ Testitud platvormid

- Victron Cerbo GX (Venus OS v3.10)
- Custom Venus OS builds (Raspberry Pi)

## 👤 Autor

Ants Stamm / insippo · 2025 · Estonia 🇪🇪
