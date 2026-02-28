# Contribuer à AMF-OS Sovereign Elite

Merci de votre intérêt pour la construction de l'avenir de l'IA souveraine ! Ce document fournit les directives et instructions pour contribuer au projet.

## Code de Conduite
En participant à ce projet, vous acceptez de respecter notre [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Comment Contribuer

### Signaler des Problèmes
1. Vérifiez les issues existantes pour éviter les doublons.
2. Utilisez les templates d'issue disponibles (Bug report ou Feature request).
3. Fournissez des étapes de reproduction détaillées.
4. Incluez les informations système (OS, version de Bun, matériel).

### Pull Requests
1. Forkez le dépôt.
2. Créez une branche de fonctionnalité : `git checkout -b feat/votre-feature`.
3. Effectuez vos modifications avec des messages de commit clairs.
4. Ajoutez des tests pour les nouvelles fonctionnalités.
5. Assurez-vous que tous les tests passent : `bun test`.
6. Soumettez votre Pull Request vers la branche `main`.

### Messages de Commit
Nous suivons les conventions standards :
- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation
- `refactor:` Refactorisation du code
- `test:` Ajout de tests
- `chore:` Maintenance

## Setup de Développement (Elite)

```bash
# Clonez votre fork
git clone https://github.com/votre-username/AMFbot-Suite.git
cd AMFbot-Suite

# Installez les dépendances avec Bun
bun install

# Lancez en mode développement
bun dev

# Exécutez les tests
bun test
```

## Style de Code
- **TypeScript** : Nous utilisons ESLint et Prettier via Bun.
- Lancez `bun run format` avant de committer.

## Licence
En contribuant, vous acceptez que vos contributions soient licenciées sous la Licence Apache 2.0.
