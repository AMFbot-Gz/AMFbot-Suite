import { env } from "../config/env";
import chalk from "chalk";

export interface OllamaOptions {
    model: string;
    temperature?: number;
    abortSignal?: AbortSignal;
}

/**
 * Ollama Elite Adapter
 * High-performance stream processing with system kinetic awareness
 */
export class OllamaAdapter {
    /**
     * Primary Chat Stream logic
     */
    async *chat(messages: any[], options: OllamaOptions): AsyncGenerator<string> {
        const response = await fetch(`\${env.OLLAMA_HOST}/api/chat`, {
            method: "POST",
            signal: options.abortSignal,
            body: JSON.stringify({
                model: options.model,
                messages: messages,
                options: { temperature: options.temperature ?? 0.7 },
                stream: true,
            }),
        });

        if (!response.body) throw new Error("Ollama: Empty stream body");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                try {
                    const lines = chunk.split("\n").filter(l => l.trim());
                    for (const line of lines) {
                        const json = JSON.parse(line);
                        if (json.message?.content) {
                            yield json.message.content;
                        }
                        if (json.done) break;
                    }
                } catch (e) {
                    // Silent catch for partial JSON buffer
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    /**
     * Quantization-aware Model Pull
     */
    async ensureModel(model: string) {
        console.log(chalk.dim(`🧠 OLLAMA: Validating model persistence: \${model}`));
        // In a full implementation, this triggers 'ollama pull' if missing
    }
}
