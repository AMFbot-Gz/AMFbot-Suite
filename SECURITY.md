# Politique de Sécurité : AMF-OS Sovereign

## Versions Supportées

| Version | Supportée           |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :warning:          |
| < 1.0   | :x:                |

## Signaler une Vulnérabilité

Si vous découvrez une faille de sécurité, merci de la signaler de manière responsable :

1. **NE PAS** ouvrir une issue publique.
2. Envoyez les détails de la vulnérabilité via un canal privé ou sécurisé (email contact@amfbot.dev - exemple).
3. Incluez :
   - Description de la faille.
   - Étapes de reproduction.
   - Impact potentiel.
   - Correctif suggéré (si possible).

## Modèle de Sécurité Sovereign

### Accès Système Privilégié
Le module d'accès d'AMF-OS est conçu avec la sécurité comme priorité absolue :
- **Confirmation Explicite** : Toutes les commandes sudo nécessitent une confirmation utilisateur.
- **Audit Logging** : Chaque action privilégiée est enregistrée dans `~/.amf-os/audit.json`.
- **Zéro Persistance** : Les identifiants root ne sont jamais stockés en mémoire.

### Isolation & Sandboxing
- **Firecracker VMM** : L'exécution des instructions complexes se fait dans un environnement isolé (sandbox).
- **Isolation Réseau** : Les conteneurs Docker tournent sur des réseaux isolés sans accès externe par défaut.

### Confidentialité Absolue
- **Traitement Local** : Toute l'intelligence artificielle est traitée localement.
- **Zéro Télémétrie** : Aucune donnée analytique ou de diagnostic n'est collectée.

## Bonnes Pratiques
1. Exécutez AMF-OS sous un utilisateur dédié si possible.
2. Vérifiez régulièrement les logs d'audit : `cat ~/.amf-os/audit.json`.
3. Utilisez des variables d'environnement pour vos tokens (Telegram, etc.).
