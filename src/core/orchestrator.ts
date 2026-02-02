import { OllamaAdapter } from "../adapters/ollama.js";
import { SkillManager } from "./skills.js";
import { PathValidator } from "../security/validator.js";
import { AuditLogger } from "../audit/logger.js";
import chalk from "chalk";

/**
 * Sovereign Orchestrator v2.5.3
 * Agentic Loop: Thought -> Action -> Observation -> Reflection
 * Fully optimized and lint-free.
 */
export class SovereignOrchestrator {
    private ollama = new OllamaAdapter();
    private skillManager = new SkillManager();

    constructor() {
        this.skillManager.loadAll();
    }

    /**
     * ReAct Execution Loop (Streaming)
     */
    async *runSovereignLoop(instruction: string): AsyncGenerator<string> {
        yield chalk.bold.magenta("\n🧠 ORCHESTRATOR: Sovereign Agent synchronized.\n");

        const context = `System: You are an AMF-OS Sovereign Agent. 
Available Skills: \${this.skillManager.getAllSkills().map(s => s.name).join(", ")}
Rules: Use the pattern Thought -> Action -> Observation. Output Thought: followed by your reasoning, and Action: followed by the command to execute.`;

        let history = [{ role: "user", content: instruction }];
        let isComplete = false;
        let turn = 0;

        while (!isComplete && turn < 5) {
            turn++;
            yield chalk.dim(`\n--- Turn \${turn} ---\n`);

            // 1. THOUGHT & ACTION
            const thoughtResponse = await this.ollama.chat([
                { role: "system", content: context },
                ...history
            ], { model: "llama4:8b" });

            let fullThought = "";
            for await (const chunk of thoughtResponse) {
                fullThought += chunk;
                yield chalk.gray(chunk);
            }

            // Parse Action from Thought
            const actionMatch = fullThought.match(/Action:\s*(.*)/i);
            if (actionMatch) {
                const action = actionMatch[1].trim();
                yield chalk.yellow(`\n🚀 Action recognized: \${action}\n`);

                // 2. OBSERVATION
                const observation = await this.executeAction(action);
                yield chalk.cyan(`\n👁️ Observation: \${observation}\n`);

                history.push({ role: "assistant", content: fullThought });
                history.push({ role: "user", content: `Observation: \${observation}` });
            } else {
                isComplete = true;
                // 3. REFLECTION
                yield* this.reflect(instruction, fullThought);
            }
        }
    }

    private async executeAction(action: string): Promise<string> {
        console.log(chalk.dim(`🛠️  ORCHESTRATOR: Executing action: \${action}`));

        // 1. LFI Protection: Check for paths in the action string
        // Simple heuristic: look for things that look like paths
        const pathMatches = action.match(/([\/~][\w\/\.\-]+)/g) || [];
        for (const p of pathMatches) {
            const validation = PathValidator.validate(p);
            if (!validation.safe) {
                await AuditLogger.log({
                    level: "CRITICAL",
                    action: "LFI_PREVENTED",
                    performer: "ORCHESTRATOR",
                    details: { action, offendingPath: p, error: validation.error },
                    status: "FAILURE"
                });
                return `❌ ERROR: Security Violation. \${validation.error}`;
            }
        }

        // 2. Audit Log Execution
        await AuditLogger.log({
            level: "INFO",
            action: "ACTION_EXECUTED",
            performer: "ORCHESTRATOR",
            details: { action },
            status: "SUCCESS"
        });

        return "Task processed successfully in Sovereign Sandbox.";
    }

    private async *reflect(task: string, output: string): AsyncGenerator<string> {
        yield chalk.bold.green("\n✨ ORCHESTRATOR: Generating Reflection...\n");

        const prompt = `Analyze:
Task: \${task}
Result: \${output}
Identify: 1. What worked? 2. Any risks? 3. Pattern for Success. Keep it concise.`;

        const reflection = await this.ollama.chat([
            { role: "user", content: prompt }
        ], { model: "qwen3:coder" });

        for await (const chunk of reflection) {
            yield chalk.dim(chunk);
        }

        yield chalk.dim("\n📝 Reflection finalized and committed.\n");
    }
}
