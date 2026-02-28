# 🛡️ Sécurité & Sandboxing : Deep Dive

La sécurité d'AMF-OS repose sur le principe du "Privilège Minimum" et de l'isolation multicouche.

## 1. Isolation Logicielle (Actuelle)
Aujourd'hui, l'agent utilise une sandbox logique (`src/autonomy/sandbox.ts`) qui :
*   **Whitelist de Commandes** : Seules les binaires explicitement autorisés peuvent être appelés.
*   **Validation de Chemin** : Empêche l'accès aux dossiers sensibles du système (`/etc`, `/root`, etc.) via des techniques de nettoyage de path.
*   **Timeout Strict** : Toute commande dépassant le temps imparti est immédiatement "killée".

## 2. Isolation VMM (Future - Blueprint 2026.1)
Nous intégrons actuellement le support de **Firecracker VMM**. 
*   **Micro-VM** : Chaque instruction complexe est exécutée dans sa propre micro-VM Linux légère.
*   **Ressources Limitées** : Chaque VM a un quota strict de CPU et RAM, rendant les attaques par déni de service impossibles sur l'hôte.
*   **Snapshotting** : Avant chaque action, un snapshot de la VM est pris, permettant un rollback instantané sans affecter l'hôte.

## 3. Sentinel : Le Système de Surveillance
Sentinel n'est pas qu'un logger ; c'est un agent autonome qui :
*   **Détection d'Anomalie** : Analyse la cinétique des commandes shell. Une séquence inhabituelle de commandes système déclenche un verrouillage préventif.
*   **Audit Immuable** : Les logs sont écrits dynamiquement et peuvent être déportés sur un nœud de stockage chiffré.

## 4. Recommandations de Sécurité
*   **User Dédié** : Ne lancez jamais AMF-OS en tant qu'utilisateur `root`.
*   **Network Namespace** : Lancez le kernel dans un namespace réseau restreint pour limiter l'accès à votre réseau local.
