export type ModelType = "thinking" | "coding" | "speed";

export interface ModelRouting {
    model: string;
    temperature: number;
}

export class ModelRouter {
    private routes: Record<ModelType, string> = {
        thinking: "llama4:8b",
        coding: "qwen3:coder",
        speed: "qwen3:0.5b",
    };

    /**
     * Routes prompt to best model based on regex patterns
     */
    route(prompt: string): ModelRouting {
        const isCoding = /code|script|function|class|bug|fix|refactor|compile/i.test(prompt);
        const isComplex = prompt.length > 500 || /analyze|architect|design|reason|logic/i.test(prompt);

        if (isCoding) {
            return { model: this.routes.coding, temperature: 0.2 };
        }

        if (isComplex) {
            return { model: this.routes.thinking, temperature: 0.7 };
        }

        // Default to speed for simple queries
        return { model: this.routes.speed, temperature: 0.5 };
    }
}
