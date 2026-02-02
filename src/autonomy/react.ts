import { Sandbox } from "./sandbox";
import { execa } from "execa";
import { env } from "../config/env";
import chalk from "chalk";

export class ReActLoop {
    private sandbox = new Sandbox();
    private maxRetries = 3;

    async execute(command: string, cwd: string = env.WORKSPACE_ROOT): Promise<string> {
        let currentCommand = command;
        let attempt = 0;

        while (attempt < this.maxRetries) {
            attempt++;

            const validation = await this.sandbox.validate(currentCommand);
            if (!validation.safe) {
                throw new Error(`Sandbox Violation: ${validation.error}`);
            }

            console.log(chalk.yellow(`🛠️  [Attempt ${attempt}] Executing: ${currentCommand}`));

            try {
                const { stdout } = await execa(currentCommand, { shell: true, cwd });
                return stdout;
            } catch (error: any) {
                console.error(chalk.red(`❌ Command failed: ${error.stderr || error.message}`));

                if (attempt >= this.maxRetries) break;

                console.log(chalk.cyan(`🧠 Self-Correction: Asking qwen3:coder to fix the error...`));
                currentCommand = await this.askForCorrection(currentCommand, error.stderr || error.message);
            }
        }

        throw new Error(`ReAct failed after ${this.maxRetries} attempts.`);
    }

    private async askForCorrection(failedCommand: string, errorMessage: string): Promise<string> {
        const prompt = `Fix this bash command. 
Command: ${failedCommand}
Error: ${errorMessage}
Output only the corrected command, nothing else.`;

        const response = await fetch(`${env.OLLAMA_HOST}/api/generate`, {
            method: "POST",
            body: JSON.stringify({
                model: "qwen3:coder",
                prompt: prompt,
                stream: false,
            }),
        });

        const data = await response.json();
        return data.response.trim().replace(/^`+|`+$/g, '');
    }
}
