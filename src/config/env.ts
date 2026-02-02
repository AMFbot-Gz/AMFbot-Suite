import { z } from "zod";
import dotenv from "dotenv";

dotenv.config();

const envSchema = z.object({
    NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
    OLLAMA_HOST: z.string().url().default("http://localhost:11434"),
    REDIS_URL: z.string().default("redis://localhost:6379"),
    ADMIN_TELEGRAM_ID: z.string().optional(),
    TELEGRAM_BOT_TOKEN: z.string().optional(),
    WORKSPACE_ROOT: z.string().default(process.cwd()),
    LOG_LEVEL: z.enum(["error", "warn", "info", "debug"]).default("info"),
});

export const env = envSchema.parse(process.env);
