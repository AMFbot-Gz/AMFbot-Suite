# Readme pour le répertoire custom_servers

Ce dossier permet à AMFbot de créer ses propres serveurs MCP.

## Comment ça fonctionne

1. Quand AMFbot détecte qu'il a besoin d'un nouvel outil, il peut créer un script Python dans ce dossier
2. Il met à jour automatiquement sa configuration MCP pour inclure le nouveau serveur
3. Le serveur devient disponible immédiatement pour les prochaines requêtes

## Structure

```
custom_servers/
├── README.md           # Ce fichier
├── my_tool.py          # Script Python MCP créé par AMFbot
├── my_tool.json        # Métadonnées du serveur
└── another_tool.py     # Un autre outil personnalisé
```

## Exemple de serveur personnalisé

```python
# my_tool.py
from mcp import Server

server = Server("my-tool")

@server.tool()
def my_function(param: str) -> str:
    """Description de l'outil."""
    return f"Résultat: {param}"

if __name__ == "__main__":
    server.run()
```

## Sécurité

- Tous les serveurs créés ici sont exécutés en local
- Vérifiez le code avant d'approuver les actions de création de serveurs
- Les serveurs sont soumis aux mêmes règles de confirmation que les autres commandes
