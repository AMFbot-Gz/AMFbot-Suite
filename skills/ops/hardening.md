---
name: Hardening & Audit Système
description: Sécurisation avancée de la station et audit des vulnérabilités.
domain: ops
tools:
  - sentinel:audit
  - sysctl:check
  - firewall:lock
version: 1.0.0
---

# 🛡️ Skill : Hardening & Audit Système

## 📋 Description
Cette compétence permet à l'agent d'auditer la configuration actuelle du système, de suggérer des mesures de durcissement et d'appliquer des règles de pare-feu restrictives.

## 🧠 Raisonnement
1. **Observation** : Vérifier l'utilisateur courant et les services exposés.
2. **Analyse** : Comparer avec les standards CIS ou le guide "Mode Durci" d'AMF-OS.
3. **Action** : Proposer un patch de configuration.
4. **Validation** : Vérifier que le durcissement n'a pas cassé les services critiques.

## 🛡️ Sécurité
- Interdiction de modifier `/etc/shadow` ou les clés SSH admin sans confirmation vocale/manuelle explicite.
- Toujours créer un backup Git avant de modifier des fichiers de configuration.
