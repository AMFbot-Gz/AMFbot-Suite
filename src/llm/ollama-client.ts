/**
 * AMFbot Ollama Client
 *
 * Wrapper around the Ollama JavaScript library providing:
 * - Connection management
 * - Model management (pull, list, delete)
 * - Streaming chat responses
 * - Health checks
 *
 * @license Apache-2.0
 */

import { Ollama } from "ollama";

export interface OllamaConfig {
    host?: string;
    timeout?: number;
}

export interface ModelInfo {
    name: string;
    size: number;
    modifiedAt: Date;
    digest: string;
}

export interface HealthCheckResult {
    healthy: boolean;
    host: string;
    version?: string;
    models?: string[];
    error?: string;
}

export interface ChatOptions {
    model: string;
    messages: Array<{
        role: "user" | "assistant" | "system";
        content: string;
        images?: string[];
    }>;
    stream?: boolean;
    temperature?: number;
    maxTokens?: number;
    systemPrompt?: string;
}

export interface GenerateOptions {
    model: string;
    prompt: string;
    system?: string;
    template?: string;
    stream?: boolean;
    raw?: boolean;
    format?: "json";
    options?: {
        temperature?: number;
        top_p?: number;
        top_k?: number;
        num_predict?: number;
    };
}

export class OllamaClient {
    private client: Ollama;
    private host: string;

    constructor(config: OllamaConfig = {}) {
        this.host = config.host || "http://localhost:11434";
        this.client = new Ollama({ host: this.host });
    }

    /**
     * Check if Ollama is running and healthy
     */
    async healthCheck(): Promise<HealthCheckResult> {
        try {
            const models = await this.client.list();

            return {
                healthy: true,
                host: this.host,
                models: models.models.map((m) => m.name),
            };
        } catch (error) {
            return {
                healthy: false,
                host: this.host,
                error: error instanceof Error ? error.message : String(error),
            };
        }
    }

    /**
     * List all available models
     */
    async listModels(): Promise<ModelInfo[]> {
        const response = await this.client.list();

        return response.models.map((m) => ({
            name: m.name,
            size: m.size,
            modifiedAt: new Date(m.modified_at),
            digest: m.digest,
        }));
    }

    /**
     * Pull a model from the Ollama registry
     */
    async pullModel(
        modelName: string,
        onProgress?: (progress: { status: string; completed?: number; total?: number }) => void
    ): Promise<void> {
        const stream = await this.client.pull({ model: modelName, stream: true });

        for await (const chunk of stream) {
            if (onProgress) {
                onProgress({
                    status: chunk.status,
                    completed: chunk.completed,
                    total: chunk.total,
                });
            }
        }
    }

    /**
     * Delete a model
     */
    async deleteModel(modelName: string): Promise<void> {
        await this.client.delete({ model: modelName });
    }

    /**
     * Check if a model is available locally
     */
    async hasModel(modelName: string): Promise<boolean> {
        const models = await this.listModels();
        return models.some(
            (m) => m.name === modelName || m.name.startsWith(`${modelName}:`)
        );
    }

    /**
     * Chat with a model (streaming)
     */
    async chat(
        options: ChatOptions
    ): Promise<AsyncGenerator<string, void, unknown>> {
        const messages = options.systemPrompt
            ? [{ role: "system" as const, content: options.systemPrompt }, ...options.messages]
            : options.messages;

        const response = await this.client.chat({
            model: options.model,
            messages,
            stream: true,
            options: {
                temperature: options.temperature ?? 0.7,
                num_predict: options.maxTokens ?? 4096,
            },
        });

        async function* streamResponse(): AsyncGenerator<string, void, unknown> {
            for await (const chunk of response) {
                yield chunk.message.content;
            }
        }

        return streamResponse();
    }

    /**
     * Chat with a model (non-streaming, returns full response)
     */
    async chatComplete(options: ChatOptions): Promise<string> {
        const messages = options.systemPrompt
            ? [{ role: "system" as const, content: options.systemPrompt }, ...options.messages]
            : options.messages;

        const response = await this.client.chat({
            model: options.model,
            messages,
            stream: false,
            options: {
                temperature: options.temperature ?? 0.7,
                num_predict: options.maxTokens ?? 4096,
            },
        });

        return response.message.content;
    }

    /**
     * Generate a response (simpler than chat)
     */
    async generate(
        options: GenerateOptions
    ): Promise<AsyncGenerator<string, void, unknown>> {
        const response = await this.client.generate({
            model: options.model,
            prompt: options.prompt,
            system: options.system,
            template: options.template,
            stream: true,
            format: options.format,
            options: options.options,
        });

        async function* streamResponse(): AsyncGenerator<string, void, unknown> {
            for await (const chunk of response) {
                yield chunk.response;
            }
        }

        return streamResponse();
    }

    /**
     * Generate embeddings for text
     */
    async embed(model: string, input: string | string[]): Promise<number[][]> {
        const response = await this.client.embed({
            model,
            input: Array.isArray(input) ? input : [input],
        });

        return response.embeddings;
    }

    /**
     * Show model information
     */
    async showModel(modelName: string): Promise<{
        license?: string;
        modelfile?: string;
        parameters?: string;
        template?: string;
    }> {
        const response = await this.client.show({ model: modelName });

        return {
            license: response.license,
            modelfile: response.modelfile,
            parameters: response.parameters,
            template: response.template,
        };
    }

    /**
     * Copy a model to a new name
     */
    async copyModel(source: string, destination: string): Promise<void> {
        await this.client.copy({ source, destination });
    }

    /**
     * Create a custom model from a Modelfile
     */
    async createModel(
        name: string,
        modelfile: string,
        onProgress?: (status: string) => void
    ): Promise<void> {
        const stream = await this.client.create({
            model: name,
            modelfile,
            stream: true,
        });

        for await (const chunk of stream) {
            if (onProgress) {
                onProgress(chunk.status);
            }
        }
    }

    /**
     * Get the underlying Ollama client
     */
    getClient(): Ollama {
        return this.client;
    }

    /**
     * Get the host URL
     */
    getHost(): string {
        return this.host;
    }
}

export default OllamaClient;
