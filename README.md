# Venus Export Limiter

See projekt piirab Victron Venus OS-is võrku eksporditavat võimsust, arvestades PV toodangut ja Multiplus väljundit. Kui võrku suunduv võimsus ületab `MAX_EXPORT_LIMIT_W`, siis skript vähendab Multiplus väljundit, et püsida lubatud piiris.

## Paigaldus

```bash
git clone http://<gitea-url>/ansible-bot/venus-export-limiter.git /data/dbus-limit
cd /data/dbus-limit
```

Muuda `config.py` vastavalt süsteemile. Käivita käsitsi või lisa cron/systemd kaudu.

## Systemd paigaldus (valikuline)

```bash
cp systemd/venus-export-limiter.service /etc/systemd/system/
systemctl daemon-reexec
systemctl enable --now venus-export-limiter.service
```

## Logide vaatamine

```bash
tail -f /data/dbus-limit/limit.log
```
