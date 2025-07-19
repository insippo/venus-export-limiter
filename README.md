# Venus Export Limiter v2.0

[![GitHub Repo](https://img.shields.io/badge/GitHub-insippo%2Fvenus--export--limiter-blue?logo=github)](https://github.com/insippo/venus-export-limiter)
[![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python)](https://www.python.org/)
[![Systemd](https://img.shields.io/badge/Systemd-supported-blue?logo=linux)](https://www.freedesktop.org/wiki/Software/systemd/)
[![Platform](https://img.shields.io/badge/Venus--OS-tested-brightgreen?logo=raspberry-pi)](https://www.victronenergy.com/live/venus-os:start)
[![Version](https://img.shields.io/badge/Version-2.0-success)](https://github.com/insippo/venus-export-limiter/tree/v2)

**Keeled:** [English](README.en.md) | [Eesti](README.md)

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

### Võimsuspiirangu muutmine

**OLULINE:** Muuda `config.py` failis `MAX_MULTIPLUS_OUTPUT_W` väärtust vastavalt oma vajadusele!

```python
# Näited erinevate piirangute jaoks:

# 15kW piirang
MAX_MULTIPLUS_OUTPUT_W = 15000      # 15 kilovatti

# 20kW piirang  
MAX_MULTIPLUS_OUTPUT_W = 20000      # 20 kilovatti

# 30kW piirang (vaikimisi)
MAX_MULTIPLUS_OUTPUT_W = 30000      # 30 kilovatti

# Muud seaded
PHASE_COUNT = 3                     # 3-faasiline (või 1 ühe faasi puhul)
MIN_OUTPUT_LIMIT_W = 1000          # Minimaalne väljundvõimsus
```

### Täielik config.py näide:

```python
# === PEAMISED SEADED ===
MAX_MULTIPLUS_OUTPUT_W = 20000      # MUUDA SEDA! Sinu soovitud piirang (W)
PHASE_COUNT = 3                     # 1 või 3 (sinu süsteemi järgi)
MIN_OUTPUT_LIMIT_W = 1000          # Minimaalne väljund (W)

# === TÄPSEMAD SEADED ===
# Järkjärgulise muutuse seaded (vältimaks Multiplus restarti)
MAX_POWER_CHANGE_PER_STEP = 1000   # Maksimaalne võimsuse muutus sammu kohta (W)
GRADUAL_ADJUSTMENT = True          # Kas kasutada järkjärgulist muutust
```

**Paigaldamise järel muuda kindlasti:**
```bash
nano /data/dbus-limit/config.py
# Muuda MAX_MULTIPLUS_OUTPUT_W oma vajaduse järgi
# Salvesta: Ctrl+X, Y, Enter

# Taaskäivita teenus
systemctl restart venus-export-limiter
```

Skript leiab Multiplus seadmed automaatselt.

### 💡 Levinud Kasutusjuhud

| Vajadus | Seadistus | Selgitus |
|---------|-----------|----------|
| **Kodumajapidamine** | `15000` | 15kW - tüüpiline koduse võrguühenduse piirang |
| **Väike ettevõte** | `20000` | 20kW - keskmise suurusega tööstuslik ühendus |
| **Suur maja/farm** | `30000` | 30kW - suur tööstuslik või põllumajanduslik objekt |
| **Korterelamu** | `25000` | 25kW - suurema korterelamu võrguühendus |

**Kuidas valida õige piirang:**
1. Vaata oma elektriühenduse lepingut (maksimaalne võimsus)
2. Võta 10-20% vähem, et olla kindel
3. Näiteks: 18kW leping → kasuta `16000` või `17000`

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

## 🔧 Tehnilised Detailid

### Kuidas töötab:
1. **Loeb Multiplus väljundvõimsust** DBus kaudu (`/Ac/Out/P`)
2. **Kontrollib, kas võimsus ületab piiri** (30kW vaikimisi)
3. **Rakendab järkjärgulist võimsuspiirangut** (1000W sammud, et vältida restarti)
4. **Kasutab otse Python DBus't** (100x kiirem kui subprocess kutsed)
5. **Cache'ib DBus objekte** optimaalse jõudluse jaoks

### Seadmete Tuvastamine:
Skript proovib automaatselt neid VEBus seadme teid:
- `com.victronenergy.vebus.ttyS4`
- `com.victronenergy.vebus.ttyO1`
- `com.victronenergy.vebus.ttyUSB0`
- `com.victronenergy.vebus.can0`

### Võimsuspiirangu Meetodid:
1. Otsene AC võimsuspiirang (`/Ac/PowerLimit`)
2. Faasipõhine piirang (`/Ac/Out/L1/PowerLimit`)
3. VE.Bus MaxPower seade (`/Settings/MaxPower`)
4. ESS tühjendusp piirang (kui Hub4 režiim aktiivne)

## 🐛 Parandatud Vead (v2.0)

### Viga 1: Kõvakodeeritud Seadme Tee
- **Probleem:** Kohatäide `'INSERT-YOUR-DEVICE-HERE'` põhjustas kohese ebaõnnestumise
- **Parandus:** Automaatne seadmete tuvastamine levinud Venus OS teedega

### Viga 2: Vale Loogika (Eksport vs Väljund)
- **Probleem:** Skript luges grid eksportvõimsust, mitte Multiplus väljundit
- **Parandus:** Täielik ümberkiri Multiplus tegeliku väljundvõimsuse lugemiseks ja piiramise

### Viga 3: Turvaauklik
- **Probleem:** Paigaldamise skript laadis koodi alla ilma tervikluse kontrollita
- **Parandus:** Lisatud commit hash'i kontroll ja turvakontrollid

### Viga 4: Multiplus Restart Probleem
- **Probleem:** Äkilised võimsuse muutused põhjustasid Multiplus restarti
- **Parandus:** Järkjärgulised võimsuse muutused (konfigureeritavad sammud) ja õiged DBus käsud

### Viga 5: Aeglane Jõudlus
- **Probleem:** Subprocess-põhised DBus kutsed olid 100-1000x aeglasemad
- **Parandus:** Otsene Python DBus objektide cache'imisega

## ⚡ Jõudluse Parandused

| Aspekt | v1.0 | v2.0 | Parandus |
|--------|------|------|----------|
| DBus Kiirus | 500-2000ms | 5-20ms | **100x kiirem** |
| Seadmete Tuvastamine | Käsitsi | Automaatne | **Konfig pole vaja** |
| Multiplus Stabiilsus | Restartib | Stabiilne | **Ei restardi** |
| Turvalisus | Haavatav | Kontrollitud | **Hash kontroll** |

## 🔒 Turvaomadused

- Commit hash'i kontroll paigaldamisel
- Root õiguste kontroll
- Kasutaja kinnitus kontrollimata uuendusteks
- Põhjalik vigade käsitlemine

## 📊 Konfiguratsiooni Valikud

⚠️ **ENNE KASUTAMIST MUUDA KINDLASTI `MAX_MULTIPLUS_OUTPUT_W` VÄÄRTUST!**

```python
# config.py
MAX_MULTIPLUS_OUTPUT_W = 30000      # ← MUUDA SEDA! Sinu võimsuspiirang (W)
PHASE_COUNT = 3                     # 1 või 3 faasiline süsteem
MIN_OUTPUT_LIMIT_W = 1000          # Minimaalne väljund (W)

# Järkjärgulise muutuse seaded (vältimaks Multiplus restarti)
MAX_POWER_CHANGE_PER_STEP = 1000   # Maksimaalne võimsuse muutus sammu kohta (W)
GRADUAL_ADJUSTMENT = True          # Luba järkjärguline muutus
```

**Kiire muutmise käsk:**
```bash
# Pärast paigaldamist
sed -i 's/MAX_MULTIPLUS_OUTPUT_W = 30000/MAX_MULTIPLUS_OUTPUT_W = 15000/' /data/dbus-limit/config.py
systemctl restart venus-export-limiter
```

## 🚨 Probleemide Lahendamine

### Levinud Probleemid:
1. **"Multiplus seadet ei leitud"** - Kontrolli VEBus ühendusi
2. **"Ligipääs keelatud"** - Käivita paigaldus root kasutajana
3. **"Multiplus ikka restartib"** - Vähenda `MAX_POWER_CHANGE_PER_STEP`
4. **"Skript liiga aeglane"** - Kontrolli, et DBus cache on lubatud

### Debug Režiim:
```bash
# Luba debug logimine
sed -i 's/level=logging.INFO/level=logging.DEBUG/' limit-control.py
systemctl restart venus-export-limiter
```

## ✅ Testitud platvormid

- Victron Cerbo GX (Venus OS v3.10+)
- Custom Venus OS builds (Raspberry Pi)
- Multiplus II süsteemid
- 3-faasil ised paigaldused

## 👤 Autor

**Ants Stamm** / insippo · 2025 · Estonia 🇪🇪

## 📝 Litsents

See projekt on antud "nagu on". Kasuta omal vastutusel.

## 🤝 Kaasaaitamine

Probleemide teatamine ja pull request'id on teretulnud! Palun testi põhjalikult enne esitamist.

---

**⚠️ Meelespea:** See skript kontrollib otse sinu Multiplus väljundvõimsust. Alati testi esmalt turvalises keskkonnas!
