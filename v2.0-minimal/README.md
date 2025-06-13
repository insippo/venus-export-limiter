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
