import { ModelRouter } from "./router.js";
import { SpeculativeEngine } from "./speculative.js";
import { env } from "../config/env.js";
import chalk from "chalk";

export class AMFAgent {
    private router = new ModelRouter();
    private speculator = new SpeculativeEngine();

    async chat(prompt: string, onUpdate: (chunk: string) => void) {
        console.log(chalk.dim(`🔍 Routing query: "\${prompt.slice(0, 30)}..."`));

        const { model, temperature } = this.router.route(prompt);

        // Speculative phase (optional/speed-up)
        if (model !== "qwen3:0.5b") {
            for await (const draft of this.speculator.draft(prompt, model)) {
                onUpdate(chalk.gray(draft.content));
            }
        }

        console.log(chalk.blue(`🚀 Executing with \${model}...`));

        const response = await fetch(`\${env.OLLAMA_HOST}/api/chat`, {
            method: "POST",
            body: JSON.stringify({
                model: model,
                messages: [{ role: "user", content: prompt }],
                options: { temperature },
                stream: true,
            }),
        });

        if (!response.body) return;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // Clear draft and show real response
        onUpdate("\r" + " ".repeat(100) + "\r");

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            try {
                const json = JSON.parse(chunk);
                if (json.message?.content) {
                    onUpdate(json.message.content);
                }
            } catch (e) {
                // Handle partial JSON or stream markers
            }
        }
    }
}

export { AMFAgent as Agent };
