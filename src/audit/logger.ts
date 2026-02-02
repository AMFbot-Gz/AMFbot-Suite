import fs from "fs-extra";
import path from "path";
import chalk from "chalk";

export interface AuditEntry {
    timestamp: string;
    level: "INFO" | "WARN" | "CRITICAL";
    action: string;
    performer: string;
    details: any;
    status: "SUCCESS" | "FAILURE";
}

/**
 * Sovereign Audit Logger
 * Standardized logging for Elite compliance.
 */
export class AuditLogger {
    private static logFile = path.join(process.env.HOME || ".", ".amfbot", "audit.log");

    static async log(entry: Omit<AuditEntry, "timestamp">) {
        const fullEntry: AuditEntry = {
            timestamp: new Date().toISOString(),
            ...entry
        };

        const logLine = JSON.stringify(fullEntry) + "\n";

        try {
            await fs.ensureDir(path.dirname(this.logFile));
            await fs.appendFile(this.logFile, logLine);

            // Console feedback for developers
            if (entry.level === "CRITICAL") {
                console.log(chalk.bgRed.white(" 🛡️  AUDIT CRITICAL "), chalk.red(entry.action));
            }
        } catch (e) {
            console.error(chalk.red("❌ AuditLogger Failure:"), e);
        }
    }
}
