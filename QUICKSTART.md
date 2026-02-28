# JARVIS AntiGravity — Quickstart (15 min)

> Lancez `./launch.command`, attendez le prompt `[JARVIS] >`, puis tapez les commandes ci-dessous.

---

## Test 1 — Réponse de base

```
[JARVIS] > Dis bonjour
```
**Attendu :** JARVIS répond oralement et dans l'overlay.

---

## Test 2 — Mémoire épisodique

```
[JARVIS] > Je m'appelle Marie
[JARVIS] > Comment je m'appelle ?
```
**Attendu :** JARVIS mémorise le prénom et le restitue sur la deuxième question.

---

## Test 3 — Pipeline ReAct complet (multi-étapes)

```
[JARVIS] > Ouvre Chrome, va sur wikipedia.org, prends une capture d'écran
           et enregistre-la dans Documents en l'appelant test.png
```
**Attendu :** JARVIS raisonne étape par étape (THINK → ACT → OBSERVE) et enchaîne automatiquement les skills `open_app`, `open_url`, `take_screenshot`, `write_file`.

---

## Test 4 — Résolution de coréférences

```
[JARVIS] > Ouvre VS Code. Ensuite, ferme-le.
```
**Attendu :** JARVIS comprend que "le" = VS Code et exécute `open_app` puis `kill_process` sur le bon processus.

---

## Test 5 — Screenshot + OCR

```
[JARVIS] > Prends une capture d'écran et fais une OCR dessus
```
**Attendu :** JARVIS capture l'écran, extrait le texte visible et lit le résultat.

---

## Test 6 — Génération de code

```
[JARVIS] > Crée un fichier Python qui calcule la factorielle de 5
```
**Attendu :** JARVIS génère le code et l'écrit dans un fichier (ex. `factorial.py`).

---

## Test 7 — Email (si configuré)

> Pré-requis : `EMAIL_USER` et `EMAIL_PASSWORD` définis dans `.env`

```
[JARVIS] > Lis mes 3 derniers emails non lus
```

---

## Commandes utiles

| Commande | Effet |
|---|---|
| `quit` / `bye` | Arrête JARVIS proprement |
| `Ctrl+C` | Interruption d'urgence |

---

## Overlay PyQt6

La fenêtre flottante (coin supérieur droit) affiche en temps réel :
- Ce que vous avez dit (transcription)
- La réponse de JARVIS
- Les actions en cours d'exécution

**Double-clic** sur l'overlay pour le masquer/afficher.
**Clic-glisser** pour le déplacer.

---

## Dashboard

Pendant l'exécution, le dashboard web est accessible sur :
**http://127.0.0.1:7070**

---

## En cas de problème

| Symptôme | Solution |
|---|---|
| `Connection refused` sur Ollama | `ollama serve` dans un autre terminal |
| Overlay absent | Vérifier `GUI_ENABLED=true` dans `.env` |
| Réponse très lente | Essayer `LLM_MODEL=mistral` (plus rapide) |
| Logs détaillés | `DEBUG=true` dans `.env` |
