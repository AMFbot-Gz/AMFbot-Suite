/**
 * AMFbot Model Manager
 *
 * Manages LLM models with:
 * - Auto-pull on first use
 * - Fallback to cloud APIs when local fails
 * - Model caching and lifecycle management
 *
 * @license Apache-2.0
 */

import { OllamaClient, ModelInfo } from "./ollama-client.js";
import { EventEmitter } from "events";

export interface ModelManagerConfig {
    ollamaHost?: string;
    defaultModel?: string;
    fallbackAPI?: {
        provider: "openai" | "anthropic" | "groq" | "replicate";
        apiKey: string;
        model?: string;
    };
    autoPull?: boolean;
}

export interface ModelCapabilities {
    supportsVision: boolean;
    supportsTools: boolean;
    contextLength: number;
    isLocal: boolean;
}

// Model capability definitions
const MODEL_CAPABILITIES: Record<string, Partial<ModelCapabilities>> = {
    "llama3.2": { supportsVision: true, supportsTools: true, contextLength: 128000 },
    "llama3.2:70b": { supportsVision: true, supportsTools: true, contextLength: 128000 },
    "mistral": { supportsVision: false, supportsTools: true, contextLength: 32000 },
    "codellama": { supportsVision: false, supportsTools: false, contextLength: 16000 },
    "gemma2": { supportsVision: false, supportsTools: false, contextLength: 8000 },
    "phi3": { supportsVision: false, supportsTools: false, contextLength: 4000 },
};

export class ModelManager extends EventEmitter {
    private config: Required<ModelManagerConfig>;
    private ollama: OllamaClient;
    private cachedModels: Map<string, ModelInfo> = new Map();
    private pullInProgress: Map<string, Promise<void>> = new Map();

    constructor(config: ModelManagerConfig = {}) {
        super();
        this.config = {
            ollamaHost: config.ollamaHost || "http://localhost:11434",
            defaultModel: config.defaultModel || "llama3.2",
            fallbackAPI: config.fallbackAPI || undefined!,
            autoPull: config.autoPull ?? true,
        };

        this.ollama = new OllamaClient({ host: this.config.ollamaHost });
    }

    /**
     * Ensure a model is available locally, pulling if necessary
     */
    async ensureModel(modelName: string): Promise<boolean> {
        // Check cache first
        if (this.cachedModels.has(modelName)) {
            return true;
        }

        // Check if model exists
        const hasModel = await this.ollama.hasModel(modelName);

        if (hasModel) {
            const models = await this.ollama.listModels();
            const model = models.find(
                (m) => m.name === modelName || m.name.startsWith(`${modelName}:`)
            );
            if (model) {
                this.cachedModels.set(modelName, model);
            }
            return true;
        }

        // Auto-pull if enabled
        if (this.config.autoPull) {
            return this.pullModel(modelName);
        }

        return false;
    }

    /**
     * Pull a model from Ollama registry
     */
    async pullModel(modelName: string): Promise<boolean> {
        // Check if pull is already in progress
        const existingPull = this.pullInProgress.get(modelName);
        if (existingPull) {
            await existingPull;
            return true;
        }

        this.emit("model-pull-start", { model: modelName });

        const pullPromise = (async () => {
            try {
                await this.ollama.pullModel(modelName, (progress) => {
                    this.emit("model-pull-progress", {
                        model: modelName,
                        ...progress,
                    });
                });

                // Update cache
                const models = await this.ollama.listModels();
                const model = models.find(
                    (m) => m.name === modelName || m.name.startsWith(`${modelName}:`)
                );
                if (model) {
                    this.cachedModels.set(modelName, model);
                }

                this.emit("model-pull-complete", { model: modelName });
                return true;
            } catch (error) {
                this.emit("model-pull-error", { model: modelName, error });
                throw error;
            } finally {
                this.pullInProgress.delete(modelName);
            }
        })();

        this.pullInProgress.set(modelName, pullPromise.then(() => { }));

        try {
            return await pullPromise;
        } catch {
            return false;
        }
    }

    /**
     * Get model capabilities
     */
    getCapabilities(modelName: string): ModelCapabilities {
        // Extract base model name (remove version tags)
        const baseName = modelName.split(":")[0];

        const knownCaps = MODEL_CAPABILITIES[baseName] || {};

        return {
            supportsVision: knownCaps.supportsVision ?? false,
            supportsTools: knownCaps.supportsTools ?? false,
            contextLength: knownCaps.contextLength ?? 4096,
            isLocal: true,
        };
    }

    /**
     * List all available models
     */
    async listModels(): Promise<ModelInfo[]> {
        const models = await this.ollama.listModels();

        // Update cache
        for (const model of models) {
            this.cachedModels.set(model.name, model);
        }

        return models;
    }

    /**
     * Get the default model name
     */
    getDefaultModel(): string {
        return this.config.defaultModel;
    }

    /**
     * Set the default model
     */
    setDefaultModel(modelName: string): void {
        this.config.defaultModel = modelName;
        this.emit("default-model-changed", { model: modelName });
    }

    /**
     * Check if fallback API is configured
     */
    hasFallbackAPI(): boolean {
        return !!this.config.fallbackAPI;
    }

    /**
     * Delete a model
     */
    async deleteModel(modelName: string): Promise<void> {
        await this.ollama.deleteModel(modelName);
        this.cachedModels.delete(modelName);
        this.emit("model-deleted", { model: modelName });
    }

    /**
     * Get model size (in bytes)
     */
    async getModelSize(modelName: string): Promise<number> {
        const cached = this.cachedModels.get(modelName);
        if (cached) {
            return cached.size;
        }

        const models = await this.ollama.listModels();
        const model = models.find(
            (m) => m.name === modelName || m.name.startsWith(`${modelName}:`)
        );

        return model?.size ?? 0;
    }

    /**
     * Get total size of all cached models
     */
    async getTotalModelsSize(): Promise<number> {
        const models = await this.ollama.listModels();
        return models.reduce((sum, m) => sum + m.size, 0);
    }

    /**
     * Recommend a model based on available hardware
     */
    recommendModel(availableRAM: number): string {
        // RAM in GB
        const ramGB = availableRAM / (1024 * 1024 * 1024);

        if (ramGB >= 64) {
            return "llama3.2:70b";
        } else if (ramGB >= 16) {
            return "llama3.2";
        } else if (ramGB >= 8) {
            return "mistral";
        } else {
            return "phi3";
        }
    }

    /**
     * Get the Ollama client instance
     */
    getOllamaClient(): OllamaClient {
        return this.ollama;
    }
}

export default ModelManager;
