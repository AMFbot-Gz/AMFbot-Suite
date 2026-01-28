# AMFbot - Comment ça marche ?

## 🧠 Architecture Simplifiée

```mermaid
graph TB
    subgraph "Interface Utilisateur"
        CLI[CLI amfbot]
        WEB[Interface Web]
    end
    
    subgraph "Cerveau - LLM"
        HYBRID[Client Hybride]
        ANTHROPIC[Anthropic Claude<br/>Computer Use]
        OLLAMA[Ollama Local<br/>Chat Simple]
    end
    
    subgraph "Corps - Contrôle Système"
        AGENT[Agent Core]
        ROOT[Root Access]
        MCP[Hub MCP]
    end
    
    subgraph "Outils Créatifs"
        VIDEO[LTX-Video<br/>Génération Vidéo]
        IMAGE[Flux.1<br/>Génération Image]
    end
    
    CLI --> AGENT
    WEB --> AGENT
    AGENT --> HYBRID
    HYBRID --> ANTHROPIC
    HYBRID --> OLLAMA
    AGENT --> ROOT
    AGENT --> MCP
    AGENT --> VIDEO
    AGENT --> IMAGE
```

## 🔄 Flux de Décision Hybride

```
Requête Utilisateur
        ↓
  ┌─────────────────┐
  │ Analyse Tâche   │
  └────────┬────────┘
           ↓
    ┌──────┴──────┐
    │ Complexe ?  │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │           │
   Oui         Non
     │           │
     ↓           ↓
┌─────────┐  ┌─────────┐
│ Claude  │  │ Ollama  │
│ (API)   │  │ (Local) │
└─────────┘  └─────────┘
```

## 📂 Organisation des Fichiers

| Dossier | Contenu | Langage |
|---------|---------|---------|
| `src/core/` | Runtime Agent | TypeScript |
| `src/llm/` | Clients LLM | TypeScript |
| `src/cli/` | Interface CLI | TypeScript |
| `modules/media-gen/` | IA Image/Vidéo | Python |
| `mcp-hub/` | Serveurs MCP | TypeScript |
| `scripts/` | Installation | Bash |

## 🔐 Sécurité

1. **Isolation Docker** : Chaque module dans son conteneur
2. **Confirmation Sudo** : Toute commande privilégiée demande approbation
3. **Audit Log** : Historique de toutes les actions
4. **Local First** : Données sur votre machine, pas dans le cloud
