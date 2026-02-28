# 🧠 Guide : Ajouter un Client LLM (Provider)

AMF-OS utilise le pattern **Adapter** pour rester agnostique vis-à-vis des serveurs d'inférence (Ollama, vLLM, Anthropic, etc.).

## 1. Créer l'Adapter
Créez un nouveau fichier dans `src/adapters/`.

```typescript
// src/adapters/anthropic.ts
import { env } from "../config/env.js";

export class AnthropicAdapter {
  async chat(messages: any[]) {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
       // ... config
    });
    return response.json();
  }
}
```

## 2. Configurer le Router
Le `ModelRouter` (`src/core/router.ts`) décide quel modèle/provider utiliser selon la tâche.

Ajoutez votre logique de sélection :
```typescript
if (prompt.includes("raisonnement profond")) {
  return { model: "claude-3-5-sonnet", adapter: "anthropic" };
}
```

## 3. Support du Streaming
Pour maintenir la performance "Zéro-Lag", votre adapter doit implémenter un `AsyncGenerator` compatible avec le `SSEBus`.

```typescript
async *streamChat(messages: any[]) {
  // Yield chunks en temps réel
}
```
