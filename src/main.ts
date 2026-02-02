import { SovereignKernel } from "./kernel/index";
import { TelegramBridge } from "./adapters/telegram";
import { SovereignOrchestrator } from "./core/orchestrator";
import { Sentinel } from "./sentinel/audit";
import { env } from "./config/env";
import boxen from "boxen";
import chalk from "chalk";

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
    process.stdout.write(chalk.magenta("amf-elite> "));

    for await (const line of console) {
        if (line.trim() === "exit") break;

        // Dispatch via orchestrator loop
        await orchestrator.runSovereignLoop(line);

        process.stdout.write(chalk.magenta("\n\namf-elite> "));
    }
}

bootLoader().catch((err) => {
    console.error(chalk.bgRed.white(" 🔥 KERNEL PANIC "), err);
    process.exit(1);
});
