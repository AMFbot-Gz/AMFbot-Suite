import { SovereignKernel } from "./kernel/index.js";
import { TelegramBridge } from "./adapters/telegram.js";
import { SovereignOrchestrator } from "./core/orchestrator.js";
import { Sentinel } from "./sentinel/audit.js";
import { env } from "./config/env.js";
import boxen from "boxen";
import chalk from "chalk";
import readline from "readline/promises";

/**
 * MAIN BOOT LOADER
 * Blueprint 2026.1
 */
async function bootLoader() {
    console.clear();
    console.log(
        boxen(
            chalk.bold.magenta("🛸 AMF-OS SOVEREIGN ELITE OS v2026.1\n") +
            chalk.dim("Status: Deep-Integrated | Mode: Micro-Kernel | Security: Zero-Trust"),
            { padding: 1, margin: 1, borderStyle: "double", borderColor: "magenta" }
        )
    );

    const kernel = new SovereignKernel();
    const sentinel = new Sentinel();
    const orchestrator = new SovereignOrchestrator();

    // 1. Initialiser les senseurs
    sentinel.startProactiveAudit();

    // 2. Boot Kernel
    await kernel.boot();

    // 3. Connect Adapters
    if (env.TELEGRAM_BOT_TOKEN) {
        const tgBridge = new TelegramBridge();
        await tgBridge.init();
    }

    // 4. Interface d'instruction souveraine
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    while (true) {
        const line = await rl.question(chalk.magenta("amf-elite> "));
        if (line.trim() === "exit") break;

        // Dispatch via orchestrator loop
        const stream = orchestrator.runSovereignLoop(line);
        for await (const chunk of stream) {
            process.stdout.write(chunk);
        }
        process.stdout.write("\n");
    }

    rl.close();
}

bootLoader().catch((err) => {
    console.error(chalk.bgRed.white(" 🔥 KERNEL PANIC "), err);
    process.exit(1);
});
