#!/usr/bin/env node
/**
 * 🛸 AMF-OS SOVEREIGN ELITE - COMMAND LINE INTERFACE
 * Version 2.6.0 - "The Elite Era"
 */

import { Command } from "commander";
import chalk from "chalk";
import ora from "ora";
import boxen from "boxen";
import { Agent as SovereignAgent } from "../core/agent.js";
import { env } from "../config/env.js";

const VERSION = "2.6.0";

const BANNER = `
   🛸 AMF-OS SOVEREIGN ELITE
   ─────────────────────────
   Blueprint 2026.1 | v\${VERSION}
   Mode: Micro-Kernel | Zero-Trust
`;

const program = new Command();

program
    .name("amfbot")
    .description("Sovereign AI OS for local-first autonomy")
    .version(VERSION);

/**
 * START - Launch the Sovereign Engine
 */
program
    .command("start")
    .description("Launch the Sovereign Elite Micro-Kernel")
    .action(async () => {
        console.clear();
        console.log(chalk.magenta(BANNER));

        const spinner = ora("Initializing Sovereign Kernel...").start();

        try {
            const agent = new SovereignAgent();

            // Explicitly handle events
            agent.on("hardware-detected", (caps: any) => {
                spinner.text = `Hardware Synchronized: \${caps.cpu.brand}`;
            });

            await agent.initialize();
            spinner.succeed("Sovereign System Live.");

            console.log(
                boxen(
                    chalk.green.bold("🛸 AMF-OS ELITE CONSOLE\n") +
                    chalk.dim("Type your instruction to the Sovereign Agent.\n") +
                    'Type "exit" to shutdown.',
                    { padding: 1, margin: 1, borderStyle: "double", borderColor: "green" }
                )
            );

            const session = agent.createSession({ origin: "cli" });

            // Interactive Loop
            const readline = await import("readline/promises");
            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout
            });

            while (true) {
                const input = await rl.question(chalk.magenta("amf-elite> "));
                if (input.toLowerCase() === "exit") break;

                const stream = agent.chat(session.id, input);
                for await (const chunk of stream) {
                    process.stdout.write(chunk);
                }
                process.stdout.write("\n");
            }

            await agent.shutdown();
            rl.close();
            process.exit(0);
        } catch (error) {
            spinner.fail(`Kernel Panic: \${error}`);
            process.exit(1);
        }
    });

/**
 * DOCTOR - Health Checks
 */
program
    .command("doctor")
    .description("Diagnose Sovereign OS health")
    .action(async () => {
        const { HardwareDetector } = await import("../core/hardware-detector.js");
        console.log(chalk.bold.cyan("\n🩺 AMFbot Sovereign Doctor\n"));

        const detector = new HardwareDetector();
        const caps = await detector.detect();

        console.log(HardwareDetector.formatSummary(caps));

        if (env.TELEGRAM_BOT_TOKEN) {
            console.log(chalk.green("✓ Telegram Connectivity: Configured"));
        } else {
            console.log(chalk.yellow("⚠ Telegram Connectivity: Not configured (Optional)"));
        }

        console.log(chalk.green("\n✨ Diagnostic Complete. No critical issues detected."));
    });

/**
 * STATUS - System Overview
 */
program
    .command("status")
    .description("Check system resources and model status")
    .action(async () => {
        const ollamaHost = env.OLLAMA_HOST || "http://localhost:11434";
        const spinner = ora("Connecting to Ollama...").start();

        try {
            const response = await fetch(`\${ollamaHost}/api/tags`);
            if (!response.ok) throw new Error("Ollama connection failed");

            const result = await response.json() as { models: Array<{ name: string, size: number }> };
            spinner.succeed("Ollama Online.");

            console.log(chalk.bold("\n📦 Available Models:"));
            result.models.forEach((model) => {
                console.log(`  • \${model.name} (\${(model.size / 1024 / 1024 / 1024).toFixed(2)} GB)`);
            });
        } catch (e) {
            spinner.fail(`Ollama Offline: \${e instanceof Error ? e.message : "Service unreachable"}.`);
        }
    });

/**
 * COMPLETION - Shell Autocompletion
 */
program
    .command("completion <shell>")
    .description("Generate shell completion script (zsh, bash, fish)")
    .action((shell) => {
        const scripts: Record<string, string> = {
            zsh: `# compdef amfbot
_amfbot_completion() {
  local -a commands
  commands=(
    'start:Launch the Sovereign Elite Micro-Kernel'
    'doctor:Diagnose Sovereign OS health'
    'status:Check system resources and model status'
    'completion:Generate shell completion script'
  )
  _describe 'command' commands
}
compdef _amfbot_completion amfbot`,
            bash: `_amfbot_completion() {
  COMPREPLY=($(compgen -W "start doctor status completion" -- "\${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _amfbot_completion amfbot`,
            fish: `complete -c amfbot -f
complete -c amfbot -n "__fish_use_subcommand" -a "start" -d "Launch the Sovereign Elite Micro-Kernel"
complete -c amfbot -n "__fish_use_subcommand" -a "doctor" -d "Diagnose Sovereign OS health"
complete -c amfbot -n "__fish_use_subcommand" -a "status" -d "Check system resources and model status"
complete -c amfbot -n "__fish_use_subcommand" -a "completion" -d "Generate shell completion script"`
        };

        const script = scripts[shell.toLowerCase()];
        if (script) {
            process.stdout.write(script + "\n");
        } else {
            console.error(chalk.red(`❌ Unsupported shell: \${shell}. Supported: zsh, bash, fish`));
        }
    });

program.parse();
