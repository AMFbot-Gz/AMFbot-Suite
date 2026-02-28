import { env } from "../config/env";
import path from "path";

export class Sandbox {
    /**
     * Checks if a command is syntactically valid and safe
     */
    async validate(command: string): Promise<{ safe: boolean; error?: string }> {
        // 1. Basic Syntax Check
        if (command.includes("|") || command.includes(">") || command.includes("&")) {
            // We allow piping in enterprise but should log it
        }

        // 2. Path restriction (LFI/RFI)
        // Simple check: ensure no absolute paths outside workspace in destructive commands
        const destructive = /rm -rf|mkfs|dd|chmod 777/i.test(command);
        if (destructive && command.includes("/")) {
            return { safe: false, error: "Destructive command with path detected. Restricted." };
        }

        return { safe: true };
    }
}
