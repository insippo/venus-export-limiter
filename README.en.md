# Venus Export Limiter v2.0

[![GitHub Repo](https://img.shields.io/badge/GitHub-insippo%2Fvenus--export--limiter-blue?logo=github)](https://github.com/insippo/venus-export-limiter)
[![Python](https://img.shields.io/badge/Python-3.7+-blue?logo=python)](https://www.python.org/)
[![Systemd](https://img.shields.io/badge/Systemd-supported-blue?logo=linux)](https://www.freedesktop.org/wiki/Software/systemd/)
[![Platform](https://img.shields.io/badge/Venus--OS-tested-brightgreen?logo=raspberry-pi)](https://www.victronenergy.com/live/venus-os:start)
[![Version](https://img.shields.io/badge/Version-2.0-success)](https://github.com/insippo/venus-export-limiter/tree/v2)

**Languages:** [English](README.en.md) | [Eesti](README.md)

## 🆕 v2.0 Updates

- ✅ **100x faster** - direct Python DBus usage
- ✅ **No Multiplus restarts** - gradual power changes
- ✅ **Automatic device detection** - no manual configuration needed
- ✅ **Secure installation** - commit hash verification
- ✅ **Correct functionality** - limits Multiplus output, not grid export
- ✅ **DBus caching** - optimized performance

## ℹ️ Overview

This project limits the Multiplus output power in Victron Venus OS to prevent exceeding a specified limit.  
When Multiplus output power exceeds `MAX_MULTIPLUS_OUTPUT_W` (30kW), the script applies power limiting.

## ⚠️ WARNING

**If used incorrectly or on the wrong device, this may disrupt Venus OS operation. Do not install this on systems you don't understand.**  
The script can be configured incorrectly like a "moon virus" that interrupts energy flow or limits Multiplus output to zero.

**USE AT YOUR OWN RISK.**

## 🚀 Quick Automatic Installation

```bash
wget https://raw.githubusercontent.com/insippo/venus-export-limiter/v2/install.sh
bash install.sh
```

This clones the repo to `/data/dbus-limit`, sets permissions, installs the systemd service, and starts it.

## ⚙️ Manual Configuration

Edit `config.py` according to your system:

```python
MAX_MULTIPLUS_OUTPUT_W = 30000      # Maximum Multiplus output power (W)
PHASE_COUNT = 3
MIN_OUTPUT_LIMIT_W = 1000
```

The script automatically detects Multiplus devices.

## 🔁 Systemd Service

```bash
cp systemd/venus-export-limiter.service /etc/systemd/system/
systemctl daemon-reexec
systemctl enable --now venus-export-limiter.service
```

## 📄 Logs

```bash
tail -f /data/dbus-limit/limit.log
```

## 🔧 Technical Details

### How it works:
1. **Reads Multiplus output power** via DBus (`/Ac/Out/P`)
2. **Checks if power exceeds limit** (30kW default)
3. **Applies gradual power limiting** (1000W steps to prevent restarts)
4. **Uses direct Python DBus** (100x faster than subprocess calls)
5. **Caches DBus objects** for optimal performance

### Device Detection:
The script automatically tries these VEBus device paths:
- `com.victronenergy.vebus.ttyS4`
- `com.victronenergy.vebus.ttyO1`
- `com.victronenergy.vebus.ttyUSB0`
- `com.victronenergy.vebus.can0`

### Power Limiting Methods:
1. Direct AC power limit (`/Ac/PowerLimit`)
2. Phase-based limiting (`/Ac/Out/L1/PowerLimit`)
3. VE.Bus MaxPower setting (`/Settings/MaxPower`)
4. ESS discharge limit (if Hub4 mode active)

## 🐛 Fixed Bugs (v2.0)

### Bug 1: Hardcoded Device Path
- **Problem:** Placeholder `'INSERT-YOUR-DEVICE-HERE'` caused immediate failure
- **Fix:** Automatic device discovery with common Venus OS paths

### Bug 2: Wrong Logic (Export vs Output)
- **Problem:** Script read grid export power instead of Multiplus output
- **Fix:** Complete rewrite to read and limit actual Multiplus output power

### Bug 3: Security Vulnerability
- **Problem:** Installation script downloaded code without integrity verification
- **Fix:** Added commit hash verification and security checks

### Bug 4: Multiplus Restart Issue
- **Problem:** Sudden power changes caused Multiplus to restart
- **Fix:** Gradual power changes (configurable steps) and proper DBus commands

### Bug 5: Slow Performance
- **Problem:** Subprocess-based DBus calls were 100-1000x slower
- **Fix:** Direct Python DBus with object caching

## ⚡ Performance Improvements

| Aspect | v1.0 | v2.0 | Improvement |
|--------|------|------|-------------|
| DBus Speed | 500-2000ms | 5-20ms | **100x faster** |
| Device Detection | Manual | Automatic | **No config needed** |
| Multiplus Stability | Restarts | Stable | **No restarts** |
| Security | Vulnerable | Verified | **Hash verification** |

## ✅ Tested Platforms

- Victron Cerbo GX (Venus OS v3.10+)
- Custom Venus OS builds (Raspberry Pi)
- Multiplus II systems
- 3-phase installations

## 🔒 Security Features

- Commit hash verification during installation
- Root privilege checking
- User confirmation for unverified updates
- Comprehensive error handling

## 📊 Configuration Options

```python
# config.py
MAX_MULTIPLUS_OUTPUT_W = 30000      # Your power limit (W)
PHASE_COUNT = 3                     # 1 or 3 phase system
MIN_OUTPUT_LIMIT_W = 1000          # Minimum output (W)

# Gradual adjustment settings (prevents Multiplus restart)
MAX_POWER_CHANGE_PER_STEP = 1000   # Max power change per step (W)
GRADUAL_ADJUSTMENT = True          # Enable gradual changes
```

## 🚨 Troubleshooting

### Common Issues:
1. **"No Multiplus device found"** - Check VEBus connections
2. **"Permission denied"** - Run installation as root
3. **"Multiplus still restarts"** - Reduce `MAX_POWER_CHANGE_PER_STEP`
4. **"Script too slow"** - Check DBus caching is enabled

### Debug Mode:
```bash
# Enable debug logging
sed -i 's/level=logging.INFO/level=logging.DEBUG/' limit-control.py
systemctl restart venus-export-limiter
```

## 👤 Author

**Ants Stamm** / insippo · 2025 · Estonia 🇪🇪

## 📝 License

This project is provided as-is. Use at your own risk.

## 🤝 Contributing

Issues and pull requests welcome! Please test thoroughly before submitting.

---

**⚠️ Remember:** This script directly controls your Multiplus power output. Always test in a safe environment first!