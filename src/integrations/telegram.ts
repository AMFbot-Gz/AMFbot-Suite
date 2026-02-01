import { Agent } from '../core/agent.js';
import { Telegraf } from 'telegraf';
import chalk from 'chalk';

export class TelegramBot {
    private token: string;
    private agent: Agent;
    private bot: Telegraf;

    constructor(token: string, agent: Agent) {
        this.token = token;
        this.agent = agent;
        this.bot = new Telegraf(this.token);
    }

    async start() {
        console.log(chalk.blue('📪 Telegram: Initializing bot...'));

        this.bot.start((ctx) => ctx.reply('Welcome to AMFbot. I am your sovereign assistant.'));

        this.bot.on('text', async (ctx) => {
            const chatId = ctx.chat.id.toString();
            const threadId = ctx.message.message_thread_id?.toString() || 'default';
            const text = ctx.message.text;

            // Context Management: Unique session per chat + thread
            const sessionLookupKey = `tg:\${chatId}:\${threadId}`;

            // Find session by metadata
            let session = await this.findSessionByOrigin(sessionLookupKey);

            if (!session) {
                console.log(chalk.dim(`📪 Telegram: Creating new session for \${sessionLookupKey}`));
                session = this.agent.createSession({
                    origin: 'telegram',
                    lookupKey: sessionLookupKey,
                    chatId,
                    threadId
                });
            }

            try {
                // Buffer chunks for Telegram as it doesn't support streaming well for text messages
                const stream = await this.agent.chat(session.id, text);
                let fullResponse = "";
                // For better UX, we could send an initial message and edit it, 
                // but for Telegram, simple buffering is safer for performance.
                for await (const chunk of stream) {
                    fullResponse += chunk;
                }

                await ctx.reply(fullResponse, {
                    reply_parameters: { message_id: ctx.message.message_id }
                });
            } catch (error) {
                console.error(chalk.red('📪 Telegram: Error during chat'), error);
                await ctx.reply(`Error: \${error instanceof Error ? error.message : "Internal error"}`);
            }
        });

        this.bot.launch();
        console.log(chalk.green('📪 Telegram: Bot is live and listening.'));

        // Enable graceful stop
        process.once('SIGINT', () => this.bot.stop('SIGINT'));
        process.once('SIGTERM', () => this.bot.stop('SIGTERM'));
    }

    private async findSessionByOrigin(lookupKey: string) {
        const sessions = await this.agent.listSessions();
        return sessions.find(s => s.metadata?.lookupKey === lookupKey);
    }
}

