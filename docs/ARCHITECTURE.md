# 🏗️ Architecture Technique : AMF-OS Sovereign Elite

Ce document détaille les entrailles technologiques de l'AMF-OS, conçu pour la performance, l'autonomie et la sécurité.

## 🌀 Le Micro-Kernel Événementiel
L'AMF-OS n'est pas une application monolithique ; c'est un **noyau réactif** basé sur l'événementiel.

*   **Runtime** : Bun (moteur JavaScript/TypeScript ultra-performant).
*   **Threading (Swarms)** : Utilisation massive de `Bun.Worker`. Chaque tâche lourde (surveillance, inférence longue, tâches système) est déportée dans un thread séparé pour garantir que le Kernel ne gèle jamais.
*   **Gestionnaire d'Événements** : Basé sur `EventEmitter` natif, permettant une communication fluide entre les workers et l'orchestrateur.

## 📡 Le Flux d'Instruction (Streaming)
Pour atteindre un **TTFT (Time To First Token) < 150ms**, l'AMF-OS utilise un flux asynchrone unifié (`AsyncGenerator`).
- **Orchestrateur** : `src/core/orchestrator.ts` émet désormais chaque pensée et action en temps réel.
- **Bénéfice** : L'interface (CLI ou Telegram) affiche instantanément le raisonnement de l'agent, offrant une transparence totale sur le cycle ReAct.

## 🩹 Boucle ReAct & Auto-Correction
L'autonomie d'AMF-OS repose sur sa capacité à comprendre et corriger ses erreurs.
*   **Fichier** : `src/autonomy/react.ts`
*   **Le Cycle** :
    1.  **Instruction** : L'utilisateur donne une commande.
    2.  **Validation** : Le `Sandbox` vérifie la syntaxe et la sécurité (LFI, RFI, Root Access).
    3.  **Exécution** : Tentative d'exécution via `execa`.
    4.  **Analyse** : Si `stderr` != null, l'erreur est envoyée au modèle `qwen3:coder`.
    5.  **Correction** : Le modèle propose une nouvelle syntaxe.
    6.  **Boucle** : Recommence jusqu'à succès (max 3 tentatives).

## 🧠 Gestion de la Mémoire (Tactical Knowledge)
Contrairement aux agents classiques, AMF-OS apprend de ses succès.
*   **LanceDB** : Stockage vectoriel local. Chaque commande réussie est indexée.
*   **KeyDB/Redis** : Utilisé comme cache "chaud" pour l'état du système et les sessions en cours.

## 🛡️ Isolation Sandbox
L'exécution n'est jamais directe sur l'hôte en mode "Production".
*   **Virtualisation** : Préparation pour l'intégration Firecracker VMM pour une isolation totale par micro-VM (WIP).
*   **Restiction** : Utilisation de `chroot` et de namespaces Linux pour limiter la visibilité du système de fichiers.

## 🧩 Elite Skill Pack & Browser Control
L'AMF-OS v2.5.4 intègre désormais le contrôle natif du navigateur et un pack de compétences d'élite :
- **Browser Control** : Navigation, scraping et automatisation web local-first.
- **Persistent Memory** : Apprentissage continu via Tactical Memory.
- **Sovereign Connectors** : Ponts sécurisés vers Telegram et les interfaces web personnalisées.
