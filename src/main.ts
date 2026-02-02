import { Agent as AMFAgent } from "./core/agent.js";
import { Sentinel } from "./sentinel/audit.js";
import { env } from "./config/env.js";
import { TelegramBridge } from "./adapters/telegram.js";
import boxen from "boxen";
import chalk from "chalk";
import readline from "readline/promises";

/**
 * MAIN BOOT LOADER
 * v2.6 "Elite Era"
 */
async function bootLoader() {
    console.clear();
    console.log(
        boxen(
            chalk.bold.magenta("🛸 AMF-OS SOVEREIGN ELITE OS v2.6\n") +
            chalk.dim("Status: Elite | Mode: Micro-Kernel | Security: Zero-Trust"),
            { padding: 1, margin: 1, borderStyle: "double", borderColor: "magenta" }
        )
    );

    const agent = new AMFAgent();
    const sentinel = new Sentinel();

    // 1. Initialiser les senseurs
    sentinel.startProactiveAudit();

    // 2. Boot Agent (Kernel + Hardware)
    await agent.initialize();

    // 3. Connect Adapters
    if (env.TELEGRAM_BOT_TOKEN) {
        try {
            const tgBridge = new TelegramBridge(agent);
            await tgBridge.init();
        } catch (e) {
            console.error(chalk.red("📪 BRIDGE: Failed to connect Telegram:"), e);
        }
    }

    // 4. Interface d'instruction souveraine (CLI)
    const session = agent.createSession({ origin: "main-boot" });
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    while (true) {
        const line = await rl.question(chalk.magenta("amf-elite> "));
        if (line.trim() === "exit") break;

        const stream = agent.chat(session.id, line);
        for await (const chunk of stream) {
            process.stdout.write(chunk);
        }
        process.stdout.write("\n");
    }

    await agent.shutdown();
    rl.close();
    process.exit(0);
}

bootLoader().catch((err) => {
    console.error(chalk.bgRed.white(" 🔥 KERNEL PANIC "), err);
    process.exit(1);
});
