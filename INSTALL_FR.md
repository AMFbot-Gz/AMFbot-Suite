<div align="center">

<img src="assets/logo.png" alt="AMF-OS Sovereign Logo" width="150">

# 🛠️ Guide d'Installation : AMF-OS Sovereign
### Devenez Souverain en quelques étapes.

</div>

---

## 🏗️ Pré-requis
* **OS** : macOS (M1/M2/M3 recommandés) ou Linux (Ubuntu/Debian).
* **RAM** : 16 Go minimum (32 Go recommandés pour llama4:8b).
* **GPU** : Compatible Metal (Mac) ou NVIDIA (Linux - drivers à jour).

---

## 🚀 Installation "Maître" (Rapide)

La méthode la plus simple pour le commun des mortels :

```bash
# 1. Clonez le dépôt
git clone https://github.com/AMFbot-Gz/AMFbot-Suite.git && cd AMFbot-Suite

# 2. Lancez le bootstrap intelligent
# Ce script installe Bun, Docker, Ollama et configure vos modèles.
bash setup/install.sh
```

---

## ⚙️ Configuration (.env)

Créez un fichier `.env` à la racine (ou laissez l'installeur le faire pour vous) :

| Variable | Description |
|----------|-------------|
| `OLLAMA_HOST` | Adresse d'Ollama (défaut: http://localhost:11434) |
| `ADMIN_TELEGRAM_ID` | Votre ID Telegram pour le contrôle à distance |
| `TELEGRAM_BOT_TOKEN` | Token de votre bot Telegram (optionnel) |

---

## 🌀 Lancement du Kernel

Une fois l'installation terminée :

```bash
# Démarrez le système complet
bun start
```

### Commandes Utiles
* `exit` : Ferme proprement le Kernel Sovereign.
* `help` : Affiche les capacités actuelles de l'IA (en cours d'extension).

---

## 🛡️ Résolution des Problèmes (FAQ)

**1. Ollama n'est pas détecté :**
Vérifiez qu'Ollama est lancé sur votre machine (`ollama serve` ou l'application bureau).

**2. Latence élevée :**
Assurez-vous que vous n'utilisez pas trop de CPU en parallèle. AMF-OS est optimisé pour utiliser le GPU.

---

<div align="center">

**Besoin d'aide ? Ouvrez une [Issue](https://github.com/AMFbot-Gz/AMFbot-Suite/issues).**

</div>
