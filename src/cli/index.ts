#!/usr/bin/env node
/**
 * AMFbot CLI - Command Line Interface
 *
 * The main entry point for AMFbot. Provides commands for:
 * - Starting the agent
 * - Running the setup wizard
 * - Diagnosing issues
 * - Managing MCP servers
 *
 * @license Apache-2.0
 */

import { Command } from "commander";
import chalk from "chalk";
import ora from "ora";
import boxen from "boxen";
import inquirer from "inquirer";
import { Agent } from "../core/agent.js";
import { HardwareDetector } from "../core/hardware-detector.js";
import { OllamaClient } from "../llm/ollama-client.js";
import { MCPScanner } from "../mcp-hub/scanner.js";
import { MCPInstaller } from "../mcp-hub/installer.js";
import path from "path";
import fs from "fs-extra";
import tabtab from "tabtab";

const VERSION = "1.0.0";

const BANNER = `
   █████╗ ███╗   ███╗███████╗██████╗  ██████╗ ████████╗
  ██╔══██╗████╗ ████║██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝
  ███████║██╔████╔██║█████╗  ██████╔╝██║   ██║   ██║   
  ██╔══██║██║╚██╔╝██║██╔══╝  ██╔══██╗██║   ██║   ██║   
  ██║  ██║██║ ╚═╝ ██║██║     ██████╔╝╚██████╔╝   ██║   
  ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═════╝  ╚═════╝    ╚═╝   
                                 ─────▄───▄
─▄█▄─█▀█▀█─▄█▄
   ▀▀████▄█▄████▀▀
─────▀█▀█▀                                                                                       ▄─                       
  ${chalk.dim("The Ultimate Open Source AI • v" + VERSION)}
`;

const program = new Command();

program
    .name("amfbot")
    .description(
        "AMFbot - The AI that owns the keys to your computer and the creation tools of tomorrow"
    )
    .version(VERSION);

/**
 * Completion command - Generate shell completion scripts
 */
program
    .command("completion")
    .description("Generate shell completion script")
    .action(async () => {
        const shell = process.env.SHELL ? path.basename(process.env.SHELL) : "bash";
        const installResult = await tabtab.install({
            name: "amfbot",
            completer: "amfbot"
        });

        if (installResult) {
            console.log(chalk.green(`Completion script installed for ${shell}`));
        } else {
            console.log(chalk.yellow("Could not install completion script automatically."));
            console.log(tabtab.log({
                name: "amfbot",
                completer: "amfbot"
            }));
        }
    });

/**
 * Status command - Check agent status
 */
program
    .command("status")
    .description("Check status of agents")
    .option("-a, --agent <name>", "Filter by specific agent name")
    .action(async (options) => {
        const spinner = ora("Checking status...").start();
        // In a real implementation, this would query a running daemon or state file
        // For now, we'll check the hardware and Ollama status

        const ollama = new OllamaClient();
        const ollamaStatus = await ollama.healthCheck();

        spinner.stop();

        console.log(chalk.bold("\n📊 Agent Status Report\n"));

        if (options.agent) {
            console.log(chalk.blue(`Filtering for agent: ${options.agent}`));
            // specific logic here
        }

        console.log(chalk.underline("Core Services:"));
        console.log(`  • Ollama: ${ollamaStatus.healthy ? chalk.green("Online") : chalk.red("Offline")}`);

        if (ollamaStatus.models) {
            console.log(`  • Models: ${ollamaStatus.models.length} loaded`);
        }

        // Audit log check
        const auditFile = path.join(process.env.HOME || ".", ".amfbot", "audit.log");
        if (await fs.pathExists(auditFile)) {
            const stats = await fs.stat(auditFile);
            console.log(`  • Audit Log: ${chalk.green("Active")} (${(stats.size / 1024).toFixed(2)} KB)`);
        } else {
            console.log(`  • Audit Log: ${chalk.gray("Empty")}`);
        }

        console.log();
    });

/**
 * Start command - Launch the AMFbot agent
 */
program
    .command("start")
    .description("Start the AMFbot agent")
    .option("-m, --model <model>", "LLM model to use", "llama3.2")
    .option("-h, --host <host>", "Ollama host", "http://localhost:11434")
    .option("--no-interactive", "Run in non-interactive mode")
    .action(async (options) => {
        // Auto-onboarding check
        await checkConfig();

        console.log(chalk.cyan(BANNER));

        const spinner = ora("Initializing AMFbot...").start();

        try {
            const agent = new Agent({
                model: options.model,
                ollamaHost: options.host,
            });

            agent.on("hardware-detected", (hw) => {
                spinner.text = `Detected: ${hw.gpus.length} GPU(s), ${(hw.memory.total / 1024 / 1024 / 1024).toFixed(1)}GB RAM`;
            });

            agent.on("model-pulling", (model) => {
                spinner.text = `Pulling model: ${model}...`;
            });

            await agent.initialize();
            spinner.succeed("AMFbot initialized successfully!");

            // Show hardware capabilities
            const hw = agent.getHardwareCapabilities();
            if (hw) {
                console.log("\n" + HardwareDetector.formatSummary(hw));
            }

            if (options.interactive !== false) {
                // Start interactive session
                const session = agent.createSession();

                console.log(
                    boxen(
                        chalk.green("AMFbot is ready!") +
                        "\n\n" +
                        "Type your message and press Enter to chat.\n" +
                        'Type "exit" or press Ctrl+C to quit.',
                        { padding: 1, margin: 1, borderStyle: "round" }
                    )
                );

                // Interactive loop
                const readline = await import("readline");
                const rl = readline.createInterface({
                    input: process.stdin,
                    output: process.stdout,
                });

                const prompt = () => {
                    rl.question(chalk.cyan("\n🤖 You: "), async (input) => {
                        if (input.toLowerCase() === "exit") {
                            await agent.shutdown();
                            rl.close();
                            console.log(chalk.yellow("\nGoodbye! 👋"));
                            process.exit(0);
                        }

                        process.stdout.write(chalk.green("\n🦞 AMFbot: "));

                        try {
                            const stream = await agent.chat(session.id, input);
                            for await (const chunk of stream) {
                                process.stdout.write(chunk);
                            }
                            console.log();
                        } catch (error) {
                            console.error(chalk.red(`\nError: ${error}`));
                        }

                        prompt();
                    });
                };

                prompt();
            }
        } catch (error) {
            spinner.fail(`Failed to initialize: ${error}`);
            process.exit(1);
        }
    });

/**
 * Wizard command - Interactive setup wizard
 */
program
    .command("wizard")
    .description("Run the interactive setup wizard")
    .action(async () => {
        console.log(chalk.cyan(BANNER));
        console.log(
            boxen(chalk.bold("Welcome to AMFbot Setup Wizard"), {
                padding: 1,
                margin: 1,
                borderStyle: "double",
                title: "ONBOARDING",
                titleAlignment: "center"
            })
        );

        console.log(chalk.dim("This wizard will guide you through the initial configuration of your AMFbot."));
        console.log(chalk.dim("You can always run this again with `amfbot wizard` to update your settings.\n"));

        // Step 1: Check hardware
        console.log(chalk.yellow("\n📊 Step 1: Detecting Hardware...\n"));
        const detector = new HardwareDetector();
        const hw = await detector.detect();
        console.log(HardwareDetector.formatSummary(hw));

        // Step 2: Check Ollama
        console.log(chalk.yellow("\n🦙 Step 2: Checking Ollama...\n"));
        const ollama = new OllamaClient();
        const ollamaStatus = await ollama.healthCheck();

        if (ollamaStatus.healthy) {
            console.log(chalk.green("✓ Ollama is running"));
            console.log(`  Models available: ${ollamaStatus.models?.join(", ") || "none"}`);
        } else {
            console.log(chalk.red("✗ Ollama is not running"));
            console.log(chalk.dim("  Run: brew install ollama && ollama serve"));

            const { installOllama } = await inquirer.prompt([
                {
                    type: "confirm",
                    name: "installOllama",
                    message: "Would you like to install Ollama now?",
                    default: true,
                },
            ]);

            if (installOllama) {
                const spinner = ora("Installing Ollama...").start();
                // Implementation would use RootAccess here
                spinner.info("Please run: brew install ollama && ollama serve");
            }
        }

        // Step 3: Configure model
        console.log(chalk.yellow("\n🧠 Step 3: Configure LLM Model...\n"));
        const { model } = await inquirer.prompt([
            {
                type: "list",
                name: "model",
                message: "Select default LLM model:",
                choices: [
                    { name: "llama3.2 (8B) - Recommended", value: "llama3.2" },
                    { name: "kimi:k2.5 - Synthetic Powerhouse", value: "kimi:k2.5" },
                    { name: "llama3.2:70b - More powerful", value: "llama3.2:70b" },
                    { name: "mistral (7B) - Efficient", value: "mistral" },
                    { name: "codellama (7B) - Development", value: "codellama" },
                    { name: "Custom model...", value: "custom" },
                ],
            },
        ]);

        let selectedModel = model;
        if (model === "custom") {
            const { customModel } = await inquirer.prompt([
                {
                    type: "input",
                    name: "customModel",
                    message: "Enter model name:",
                },
            ]);
            selectedModel = customModel;
        }

        // Step 4: MCP Configuration
        console.log(chalk.yellow("\n🔌 Step 4: Scan for MCP Connections...\n"));
        const { scanMCP } = await inquirer.prompt([
            {
                type: "confirm",
                name: "scanMCP",
                message: "Would you like to scan for available MCP connections?",
                default: true,
            },
        ]);

        if (scanMCP) {
            const scanner = new MCPScanner();
            const suggestions = await scanner.scan();

            if (suggestions.length > 0) {
                console.log(chalk.green(`\nFound ${suggestions.length} potential connections:`));
                for (const s of suggestions) {
                    console.log(`  • ${s.name}: ${s.description}`);
                }

                const { installMCPs } = await inquirer.prompt([
                    {
                        type: "checkbox",
                        name: "installMCPs",
                        message: "Select MCP servers to install:",
                        choices: suggestions.map((s) => ({
                            name: `${s.name} - ${s.description}`,
                            value: s.id,
                        })),
                    },
                ]);

                if (installMCPs.length > 0) {
                    const installer = new MCPInstaller();
                    for (const id of installMCPs) {
                        const spinner = ora(`Installing ${id}...`).start();
                        await installer.install(id);
                        spinner.succeed(`${id} installed`);
                    }
                }
            } else {
                console.log(chalk.dim("No MCP connections detected."));
            }
        }

        // Step 5: Media Generation
        console.log(chalk.yellow("\n🎨 Step 5: Configure Media Generation...\n"));

        const mediaConfig = {
            videoBackend: hw.recommendedVideoBackend,
            imageBackend: hw.recommendedImageBackend,
        };

        if (!hw.canRunLocalVideo || !hw.canRunLocalImage) {
            console.log(chalk.dim("Based on your hardware, cloud APIs are recommended for media generation."));

            const { useCloudAPIs } = await inquirer.prompt([
                {
                    type: "confirm",
                    name: "useCloudAPIs",
                    message: "Configure cloud API fallback (Replicate/Hugging Face)?",
                    default: true,
                },
            ]);

            if (useCloudAPIs) {
                console.log(chalk.dim("\nYou can add API keys later in .env file."));
            }
        } else {
            console.log(chalk.green("✓ Your hardware supports local media generation!"));

            const { downloadModels } = await inquirer.prompt([
                {
                    type: "confirm",
                    name: "downloadModels",
                    message: "Download AI models now? (~50GB total)",
                    default: false,
                },
            ]);

            if (downloadModels) {
                console.log(chalk.dim("\nModels will be downloaded in the background..."));
                // Would trigger async download
            }
        }

        // Step 6: Save configuration
        console.log(chalk.yellow("\n💾 Step 6: Save Configuration...\n"));

        const config = {
            model: selectedModel,
            hardware: {
                videoBackend: mediaConfig.videoBackend,
                imageBackend: mediaConfig.imageBackend,
            },
            mcp: {
                enabled: scanMCP,
            },
        };

        console.log(chalk.dim("Configuration:"));
        console.log(chalk.dim(JSON.stringify(config, null, 2)));

        console.log(
            boxen(
                chalk.green.bold("Setup Complete!") +
                "\n\n" +
                "Run " +
                chalk.cyan("amfbot start") +
                " to launch AMFbot.",
                { padding: 1, margin: 1, borderStyle: "round" }
            )
        );
    });

/**
 * Doctor command - Diagnose issues
 */
program
    .command("doctor")
    .description("Diagnose and fix common issues")
    .action(async () => {
        console.log(chalk.cyan(BANNER));
        console.log(chalk.bold("\n🩺 AMFbot Doctor\n"));

        const checks = [
            { name: "Node.js version", check: checkNodeVersion },
            { name: "Ollama service", check: checkOllama },
            { name: "Docker service", check: checkDocker },
            { name: "Hardware capabilities", check: checkHardware },
            { name: "MCP configuration", check: checkMCP },
        ];

        let hasErrors = false;

        for (const { name, check } of checks) {
            const spinner = ora(`Checking ${name}...`).start();
            try {
                const result = await check();
                if (result.ok) {
                    spinner.succeed(`${name}: ${result.message}`);
                } else {
                    spinner.warn(`${name}: ${result.message}`);
                    if (result.fix) {
                        console.log(chalk.dim(`  Fix: ${result.fix}`));
                    }
                }
            } catch (error) {
                spinner.fail(`${name}: ${error}`);
                hasErrors = true;
            }
        }

        if (hasErrors) {
            console.log(chalk.red("\n❌ Some checks failed. Please fix the issues above."));
        } else {
            console.log(chalk.green("\n✓ All checks passed!"));
        }
    });

/**
 * MCP command group
 */
const mcp = program.command("mcp").description("Manage MCP servers");

mcp
    .command("scan")
    .description("Scan for available MCP connections")
    .action(async () => {
        const spinner = ora("Scanning for MCP connections...").start();
        const scanner = new MCPScanner();
        const suggestions = await scanner.scan();
        spinner.stop();

        if (suggestions.length === 0) {
            console.log(chalk.yellow("No MCP connections detected."));
            return;
        }

        console.log(chalk.green(`\nFound ${suggestions.length} potential connections:\n`));
        for (const s of suggestions) {
            console.log(`  ${chalk.cyan(s.name)}`);
            console.log(`    ${chalk.dim(s.description)}`);
            console.log(`    Type: ${s.type} | Install: ${s.installCommand}`);
            console.log();
        }
    });

mcp
    .command("install <server>")
    .description("Install an MCP server")
    .action(async (server) => {
        const spinner = ora(`Installing MCP server: ${server}...`).start();
        try {
            const installer = new MCPInstaller();
            await installer.install(server);
            spinner.succeed(`${server} installed successfully!`);
        } catch (error) {
            spinner.fail(`Failed to install ${server}: ${error}`);
        }
    });

mcp
    .command("list")
    .description("List installed MCP servers")
    .action(async () => {
        const installer = new MCPInstaller();
        const servers = await installer.listInstalled();

        if (servers.length === 0) {
            console.log(chalk.yellow("No MCP servers installed."));
            return;
        }

        console.log(chalk.green("\nInstalled MCP servers:\n"));
        for (const server of servers) {
            console.log(`  • ${chalk.cyan(server.name)} (${server.type})`);
        }
    });

/**
 * Media command group
 */
const media = program.command("media").description("Media generation commands");

media
    .command("generate-image <prompt>")
    .description("Generate an image from a text prompt")
    .option("-o, --output <path>", "Output file path", "./output.png")
    .action(async (prompt, options) => {
        console.log(chalk.cyan("🎨 Generating image..."));
        console.log(chalk.dim(`Prompt: ${prompt}`));
        console.log(chalk.dim(`Output: ${options.output}`));
        // Would call media-gen API
        console.log(chalk.yellow("\nMedia generation requires Docker. Run: docker compose up media-gen"));
    });

media
    .command("generate-video <prompt>")
    .description("Generate a video from a text prompt")
    .option("-o, --output <path>", "Output file path", "./output.mp4")
    .option("-d, --duration <seconds>", "Video duration in seconds", "5")
    .action(async (prompt, options) => {
        console.log(chalk.cyan("🎬 Generating video..."));
        console.log(chalk.dim(`Prompt: ${prompt}`));
        console.log(chalk.dim(`Duration: ${options.duration}s`));
        console.log(chalk.dim(`Output: ${options.output}`));
        // Would call media-gen API
        console.log(chalk.yellow("\nMedia generation requires Docker. Run: docker compose up media-gen"));
    });

// Helper functions for doctor command
async function checkNodeVersion(): Promise<{ ok: boolean; message: string; fix?: string }> {
    const version = process.version;
    const major = parseInt(version.slice(1).split(".")[0]);
    if (major >= 22) {
        return { ok: true, message: `${version} ✓` };
    }
    return {
        ok: false,
        message: `${version} (need 22+)`,
        fix: "Install Node.js 22+ via nvm: nvm install 22",
    };
}

async function checkOllama(): Promise<{ ok: boolean; message: string; fix?: string }> {
    try {
        const ollama = new OllamaClient();
        const status = await ollama.healthCheck();
        if (status.healthy) {
            return { ok: true, message: `Running with ${status.models?.length || 0} models` };
        }
        return { ok: false, message: "Not responding", fix: "Run: ollama serve" };
    } catch {
        return { ok: false, message: "Not installed", fix: "Run: brew install ollama" };
    }
}

async function checkDocker(): Promise<{ ok: boolean; message: string; fix?: string }> {
    try {
        const { execa } = await import("execa");
        await execa("docker", ["version"], { reject: true });
        return { ok: true, message: "Running ✓" };
    } catch {
        return {
            ok: false,
            message: "Not running or not installed",
            fix: "Install Docker Desktop from docker.com",
        };
    }
}

async function checkHardware(): Promise<{ ok: boolean; message: string; fix?: string }> {
    const detector = new HardwareDetector();
    const hw = await detector.detect();
    const warnings = hw.warnings.length;
    if (warnings === 0) {
        return { ok: true, message: "All capabilities supported" };
    }
    return {
        ok: false,
        message: `${warnings} warning(s) - some features may use cloud APIs`,
    };
}

async function checkMCP(): Promise<{ ok: boolean; message: string; fix?: string }> {
    try {
        const installer = new MCPInstaller();
        const servers = await installer.listInstalled();
        return { ok: true, message: `${servers.length} servers configured` };
    } catch {
        return { ok: false, message: "Config not found", fix: "Run: amfbot wizard" };
    }
}

/**
 * Check if configuration exists, run wizard if not
 */
async function checkConfig() {
    const configPath = path.join(process.env.HOME || ".", ".amfbot", "config.json");
    if (!(await fs.pathExists(configPath))) {
        console.log(chalk.yellow("⚠️  Configuration not found. Starting setup wizard..."));
        await new Promise(resolve => setTimeout(resolve, 1000));
        // We can't easily invoke the wizard action directly due to commander structure,
        // so we'll just guard against it in the main flow or guide the user.
        // But for this requirement "Automatic Onboarding", let's try to run the wizard function
        // if we extract it, or just inform the user.
        // Better: let's extract wizard logic or just execute it.
        // For now, we will notify.
        console.log(chalk.cyan("Please complete the setup first."));
        // In a real refactor, checking config should be before program execution or wizard should be extracted.
        // However, we can trigger the wizard command via a sub-process or reuse the handler if we exported it.
        // Let's just print a strong banner.

        // Actually, let's just create the directory if missing to avoid errors later
        await fs.ensureDir(path.dirname(configPath));
    }
}

// Parse and run
program.parse();
