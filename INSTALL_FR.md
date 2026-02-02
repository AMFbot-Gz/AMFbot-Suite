<div align="center">

<img src="assets/logo.png" alt="AMF-OS Sovereign Logo" width="150">

# 🛠️ Guide d'Installation : AMF-OS Sovereign
### Devenez Souverain selon votre profil.

</div>

---

## 🏗️ Prérequis Systèmes
Avant de commencer, vérifiez que votre machine dispose des ressources nécessaires :
- **CPU** : 4 cœurs minimum.
- **RAM** : 16 Go minimum (32 Go pour le modèle `llama4:8b` complet).
- **GPU** : Compatible Metal (Mac M1/M2/M3) ou NVIDIA (Drivers 535+ recommandés).
- **Réseau** : Ports 11434 (Ollama) et 6379 (Redis) libres.

---

## 🥇 Niveau 1 : Utilisateur Standard (One-Click)
*Pour ceux qui veulent une station de travail prête à l'emploi avec une intervention minimale.*

Cette méthode utilise notre script intelligent qui configure tout automatiquement.

```bash
# 1. Clonez le dépôt
git clone https://github.com/AMFbot-Gz/AMFbot-Suite.git && cd AMFbot-Suite

# 2. Exécutez l'installation automatique
# Ce script s'occupe de Bun, Docker, Ollama et de vos modèles LLM.
bash setup/install.sh

# 3. Lancez le système
bun start
```

---

## 🥈 Niveau 2 : Power User (Full Docker)
*Pour ceux qui préfèrent une isolation totale du système et une gestion via conteneurs.*

Assurez-vous d'avoir installé **Docker** et **Docker Compose**.

1.  Configurez votre environnement :
    ```bash
    cp .env.example .env
    # Éditez .env avec vos clés Telegram et vos préférences
    ```
2.  Lancez la pile complète :
    ```bash
    docker-compose up -d --build
    ```
3.  Accédez aux logs du noyau :
    ```bash
    docker logs -f amf-os-kernel
    ```

---

## 🥉 Niveau 3 : Développeur (Contribution & Debug)
*Pour ceux qui souhaitent modifier le Kernel, ajouter des modules ou exécuter des tests.*

1.  Installation des dépendances de développement :
    ```bash
    bun install
    ```
2.  Lancement en mode "Watch" (le Kernel redémarre à chaque modification) :
    ```bash
    bun dev
    ```
3.  Exécution de la suite de tests :
    ```bash
    bun test
    ```
4.  Vérification de la qualité du code :
    ```bash
    bun run lint
    bun run format
    ```

---

## ⚙️ Configuration du .env (Détails)

| Variable | Usage | Valeur par défaut |
|----------|-------|-------------------|
| `OLLAMA_HOST` | Adresse du cerveau AI | `http://localhost:11434` |
| `ADMIN_TELEGRAM_ID` | Votre ID unique pour le contrôle | `Obligatoire` |
| `REDIS_URL` | Cache chaud pour l'état | `redis://localhost:6379` |
| `LOG_LEVEL` | Précision des logs | `info` |

---

<div align="center">

**Un problème ? Consultez les [Issues](https://github.com/AMFbot-Gz/AMFbot-Suite/issues) ou ouvrez une Discussion.**

</div>
