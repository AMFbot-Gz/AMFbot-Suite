import { Telegraf } from "telegraf";
import { AMFAgent } from "../core/agent";
import { env } from "../config/env";
import chalk from "chalk";

export class TelegramBridge {
    private bot: Telegraf;
    private agent = new AMFAgent();

    constructor() {
        if (!env.TELEGRAM_BOT_TOKEN) throw new Error("TELEGRAM_BOT_TOKEN missing");
        this.bot = new Telegraf(env.TELEGRAM_BOT_TOKEN);
    }

    async start() {
        console.log(chalk.blue("📪 Telegram: Secure Bridge Initializing..."));

        this.bot.on("text", async (ctx) => {
            const senderId = ctx.from.id.toString();

            // STRICT ADMIN LOCK
            if (env.ADMIN_TELEGRAM_ID && senderId !== env.ADMIN_TELEGRAM_ID) {
                console.warn(chalk.red(`⚠️  Unauthorized access attempt from ID: ${senderId}`));
                return ctx.reply("❌ AMF-OS: Access Denied. Sender ID not in whitelist.");
            }

            const prompt = ctx.message.text;

            await ctx.sendChatAction("typing");

            let responseBuffer = "";
            await this.agent.chat(prompt, (chunk) => {
                responseBuffer += chunk;
            });

            await ctx.reply(responseBuffer || "No response generated.");
        });

        this.bot.launch();
        console.log(chalk.green("📪 Telegram: Bridge Live (Admin Only)"));
    }
}
