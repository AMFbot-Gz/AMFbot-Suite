import { env } from "../config/env";

export interface SpeculativeResult {
    content: string;
    isDraft: boolean;
}

/**
 * Speculative Decoding Helper
 * Perceived latency reduction by drafting with 0.5b model
 */
export class SpeculativeEngine {
    private smallModel = "qwen3:0.5b";

    /**
     * Stream a draft to the UI immediately, then refine
     * Note: This is a simplified coordination logic for the CLI layer
     */
    async *draft(prompt: string, targetModel: string): AsyncGenerator<SpeculativeResult> {
        // 1. Kick off drafting
        const draftResponse = await fetch(`${env.OLLAMA_HOST}/api/generate`, {
            method: "POST",
            body: JSON.stringify({
                model: this.smallModel,
                prompt: `[DRAFT MODE] ${prompt}`,
                stream: false,
            }),
        });

        if (draftResponse.ok) {
            const data = await draftResponse.json();
            yield { content: data.response, isDraft: true };
        }

        // 2. The full agent will handle the 'Target Model' refinement separately 
        // to avoid blocking the initial visual hit.
    }
}
