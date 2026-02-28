# 🛠️ Guide : Créer un Nouveau Module

L'architecture modulaire d'AMF-OS permet d'ajouter des capacités facilement. Voici comment créer un module (ex: `vps-control`).

## 1. Structure du Fichier
Créez votre fichier dans `src/modules/` ou un dossier dédié.

```typescript
// src/modules/vps-control.ts
import { execa } from "execa";
import chalk from "chalk";

export class VPSControl {
  /**
   * Redémarre un serveur via SSH
   */
  async restartServer(ip: string): Promise<string> {
    console.log(chalk.cyan(`📡 VPS: Redémarrage de \${ip}...`));
    // Logique d'exécution via le Kernel ou direct
    return "Initialisation du reboot...";
  }
}
```

## 2. Intégration à l'Orchestrateur
Pour que l'IA puisse utiliser ce module, vous devez l'enregistrer dans `src/core/orchestrator.ts`.

1.  Importez votre classe.
2.  Ajoutez-la aux outils disponibles.
3.  Mettez à jour le prompt système pour informer l'IA de cette nouvelle capacité.

## 3. Sécurité (Sandbox)
Si votre module exécute des commandes système, assurez-vous de mettre à jour `src/autonomy/sandbox.ts` pour autoriser les nouvelles binaires (ex: `ssh`).

```typescript
const ALLOWED_COMMANDS = ["npm", "git", "bun", "ssh"]; // Ajoutez ssh ici
```

## 4. Test
Chaque module doit avoir son fichier de test :
`bun test src/__tests__/vps-control.test.ts`
