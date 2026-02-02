import { Telegraf } from "telegraf";
import { env } from "../config/env";
import chalk from "chalk";

/**
 * Telegram Elite Bridge
 * Supports Secure Admin Routing + Multi-modal Payloads
 */
export class TelegramBridge {
    private bot: Telegraf;

    constructor() {
        if (!env.TELEGRAM_BOT_TOKEN) throw new Error("TELEGRAM_BOT_TOKEN missing");
        this.bot = new Telegraf(env.TELEGRAM_BOT_TOKEN);
    }

    async init() {
        console.log(chalk.blue("📪 BRIDGE: Initializing Telegram Elite Router..."));

        this.bot.on("message", async (ctx) => {
            const senderId = ctx.from.id.toString();

            // ADMIN LOCK
            if (env.ADMIN_TELEGRAM_ID && senderId !== env.ADMIN_TELEGRAM_ID) {
                return ctx.reply("❌ OS: Access Denied. Sender unauthorized.");
            }

            // Handle multimodal (Photo/File) or Text
            if ("text" in ctx.message) {
                this.handleText(ctx);
            } else if ("photo" in ctx.message) {
                this.handlePhoto(ctx);
            }
        });

        this.bot.launch();
        console.log(chalk.green("📪 BRIDGE: Telegram Elite Active."));
    }

    private async handleText(ctx: any) {
        const text = ctx.message.text;
        // Dispatch to Kernel event loop
        console.log(chalk.dim(`📪 BRIDGE: Incoming instruction from Admin: \${text}`));
        // Kernel trigger here
    }

    private async handlePhoto(ctx: any) {
        // Process image buffer for OCR or Vision tools
        const photo = ctx.message.photo[ctx.message.photo.length - 1];
        const link = await ctx.telegram.getFileLink(photo.file_id);
        console.log(chalk.dim(`📪 BRIDGE: Incoming visual payload: \${link.href}`));
    }
}
