# ⚔️ Guide "Mode Durci" (Hardened Mode)

Pour les déploiements en environnement critique (Ops, Infrastructure), suivez ces étapes pour verrouiller votre station AMF-OS.

## 1. Utilisateur Médian
Créez un utilisateur système sans privilèges sudo pour faire tourner le kernel.

```bash
sudo useradd -m amf-kernel
sudo -u amf-kernel bash setup/install.sh
```

## 2. Isolation via Systemd
Si vous utilisez notre service systemd, activez les options de durcissement :

```ini
[Service]
# Durcissement systemd
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/Users/wiaamhadara/AMFbot-Suite/data
NoNewPrivileges=true
```

## 3. Restriction des Volumes Docker
Si vous utilisez Docker, montez les volumes en `ro` (read-only) partout où l'écriture n'est pas strictement nécessaire.

```yaml
volumes:
  - ./config:/app/config:ro
  - ./logs:/app/logs:rw
```

## 4. Surveillance Sentinel
Activez le mode "Panic On Violation" dans votre `.env` :
`SENTINEL_PANIC_THRESHOLD=1`
Le kernel s'arrêtera au moindre signal suspect.
