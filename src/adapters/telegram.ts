import { Telegraf } from "telegraf";
import { env } from "../config/env.js";
import { Agent as AMFAgent } from "../core/agent.js";
import chalk from "chalk";

/**
 * Telegram Elite Bridge v2.6
 * Synchronized with Sovereign AMFAgent.
 */
export class TelegramBridge {
    private bot: Telegraf;
    private agent: AMFAgent;

    constructor(agent: AMFAgent) {
        if (!env.TELEGRAM_BOT_TOKEN) throw new Error("TELEGRAM_BOT_TOKEN missing");
        this.bot = new Telegraf(env.TELEGRAM_BOT_TOKEN);
        this.agent = agent;
    }

    async init() {
        console.log(chalk.blue("📪 BRIDGE: Initializing Telegram Elite Router..."));

        this.bot.on("message", async (ctx: any) => {
            const senderId = ctx.from.id.toString();

            // ADMIN LOCK
            if (env.ADMIN_TELEGRAM_ID && senderId !== env.ADMIN_TELEGRAM_ID) {
                return ctx.reply("❌ OS: Access Denied. Sender unauthorized.");
            }

            if ("text" in ctx.message) {
                await this.handleText(ctx);
            }
        });

        this.bot.launch();
        console.log(chalk.green("📪 BRIDGE: Telegram Elite Active."));
    }

    private async handleText(ctx: any) {
        const text = ctx.message.text;
        const chatId = ctx.chat.id.toString();

        console.log(chalk.dim(`📪 BRIDGE: Incoming instruction from Admin: \${text}`));

        // Create or get session for this chat
        const session = this.agent.createSession({ origin: "telegram", chatId });

        try {
            const stream = this.agent.chat(session.id, text);
            let responseBuffer = "";
            const message = await ctx.reply("💬 Sovereign Agent réfléchit...");

            for await (const chunk of stream) {
                responseBuffer += chunk;
                // Optional: Update telegram message for real-time feel
                // In a production environment, you'd throttle this to avoid Telegram rate limits.
            }

            await ctx.telegram.editMessageText(
                ctx.chat.id,
                message.message_id,
                undefined,
                responseBuffer || "Mission accomplie."
            );
        } catch (e) {
            console.error(chalk.red("❌ BRIDGE Error:"), e);
            ctx.reply(`❌ Une erreur est survenue : \${e instanceof Error ? e.message : "Erreur inconnue"}`);
        }
    }
}
