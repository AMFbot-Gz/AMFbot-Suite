/**
 * AMFbot Root Access Module
 *
 * Provides secure execution of privileged commands with user confirmation.
 * This module ensures that:
 * - All sudo operations require explicit user confirmation
 * - Confirmations are time-limited (TTL)
 * - All privileged actions are logged
 *
 * @license Apache-2.0
 */

import { EventEmitter } from "events";
import { createInterface, Interface } from "readline";
import { execa } from "execa";
import { appendFile, mkdir } from "fs/promises";
import { join } from "path";
import { homedir } from "os";

export interface RootAccessConfig {
    /** Time-to-live for sudo session in milliseconds (default: 5 minutes) */
    sessionTTL?: number;
    /** Path to store audit logs */
    logPath?: string;
    /** Whether to always require confirmation (bypass session) */
    alwaysConfirm?: boolean;
}

export interface CommandResult {
    success: boolean;
    stdout: string;
    stderr: string;
    exitCode: number;
    command: string;
    timestamp: Date;
}

export interface AuditLogEntry {
    timestamp: Date;
    command: string;
    approved: boolean;
    result?: CommandResult;
    user: string;
}

export class RootAccess extends EventEmitter {
    private config: Required<RootAccessConfig>;
    private sessionExpiry: Date | null = null;
    private readline: Interface | null = null;

    constructor(config: RootAccessConfig = {}) {
        super();
        this.config = {
            sessionTTL: config.sessionTTL ?? 5 * 60 * 1000, // 5 minutes
            logPath: config.logPath ?? join(homedir(), ".amfbot", "audit.log"),
            alwaysConfirm: config.alwaysConfirm ?? false,
        };
    }

    /**
     * Check if there's an active sudo session
     */
    hasActiveSession(): boolean {
        if (this.config.alwaysConfirm) return false;
        if (!this.sessionExpiry) return false;
        return new Date() < this.sessionExpiry;
    }

    /**
     * Start a new sudo session
     */
    startSession(): void {
        this.sessionExpiry = new Date(Date.now() + this.config.sessionTTL);
        this.emit("session-started", {
            expiresAt: this.sessionExpiry,
            ttl: this.config.sessionTTL,
        });
    }

    /**
     * End the current sudo session
     */
    endSession(): void {
        this.sessionExpiry = null;
        this.emit("session-ended");
    }

    /**
     * Request user confirmation for a privileged operation
     */
    async requestConfirmation(message: string): Promise<boolean> {
        if (this.hasActiveSession()) {
            this.emit("confirmation-skipped", { reason: "active-session" });
            return true;
        }

        this.emit("confirmation-requested", { message });

        // Create readline interface for interactive confirmation
        this.readline = createInterface({
            input: process.stdin,
            output: process.stdout,
        });

        return new Promise((resolve) => {
            const warningBox = `
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  ROOT ACCESS CONFIRMATION REQUIRED                      │
├─────────────────────────────────────────────────────────────┤
│  ${message.padEnd(57)}  │
├─────────────────────────────────────────────────────────────┤
│  This operation requires elevated privileges.               │
│  Type 'yes' to confirm, 'session' for 5-min session,       │
│  or 'no' to cancel.                                         │
└─────────────────────────────────────────────────────────────┘
`;

            console.log(warningBox);

            this.readline!.question("Confirm [yes/session/no]: ", (answer) => {
                this.readline!.close();
                this.readline = null;

                const normalizedAnswer = answer.toLowerCase().trim();

                if (normalizedAnswer === "yes" || normalizedAnswer === "y") {
                    this.emit("confirmation-granted", { type: "single" });
                    resolve(true);
                } else if (normalizedAnswer === "session" || normalizedAnswer === "s") {
                    this.startSession();
                    this.emit("confirmation-granted", { type: "session" });
                    resolve(true);
                } else {
                    this.emit("confirmation-denied");
                    resolve(false);
                }
            });
        });
    }

    /**
     * Execute a command with user confirmation if needed
     */
    async executeWithConfirmation(
        command: string,
        description: string
    ): Promise<CommandResult> {
        const confirmed = await this.requestConfirmation(description);

        if (!confirmed) {
            const deniedResult: CommandResult = {
                success: false,
                stdout: "",
                stderr: "Operation cancelled by user",
                exitCode: -1,
                command,
                timestamp: new Date(),
            };

            await this.logAuditEntry({
                timestamp: new Date(),
                command,
                approved: false,
                user: process.env.USER || "unknown",
            });

            return deniedResult;
        }

        return this.execute(command);
    }

    /**
     * Execute a privileged command (assumes confirmation already obtained)
     */
    async execute(command: string): Promise<CommandResult> {
        const timestamp = new Date();

        try {
            this.emit("command-executing", { command, timestamp });

            const result = await execa(command, {
                shell: true,
                reject: false,
            });

            const commandResult: CommandResult = {
                success: result.exitCode === 0,
                stdout: result.stdout,
                stderr: result.stderr,
                exitCode: result.exitCode ?? -1,
                command,
                timestamp,
            };

            await this.logAuditEntry({
                timestamp,
                command,
                approved: true,
                result: commandResult,
                user: process.env.USER || "unknown",
            });

            this.emit("command-complete", commandResult);
            return commandResult;
        } catch (error) {
            const errorResult: CommandResult = {
                success: false,
                stdout: "",
                stderr: error instanceof Error ? error.message : String(error),
                exitCode: -1,
                command,
                timestamp,
            };

            await this.logAuditEntry({
                timestamp,
                command,
                approved: true,
                result: errorResult,
                user: process.env.USER || "unknown",
            });

            this.emit("command-error", { command, error });
            return errorResult;
        }
    }

    /**
     * Execute a sudo command
     */
    async executeSudo(
        command: string,
        description?: string
    ): Promise<CommandResult> {
        const sudoCommand = `sudo ${command}`;
        return this.executeWithConfirmation(
            sudoCommand,
            description || `Execute: ${sudoCommand}`
        );
    }

    /**
     * Install a package using the system package manager
     */
    async installPackage(
        packageName: string,
        manager: "brew" | "apt" | "npm" | "pip" = "brew"
    ): Promise<CommandResult> {
        const commands: Record<string, string> = {
            brew: `brew install ${packageName}`,
            apt: `sudo apt-get install -y ${packageName}`,
            npm: `npm install -g ${packageName}`,
            pip: `pip install ${packageName}`,
        };

        const command = commands[manager];
        const needsSudo = manager === "apt";

        if (needsSudo) {
            return this.executeSudo(
                `apt-get install -y ${packageName}`,
                `Install package: ${packageName} using apt`
            );
        }

        return this.executeWithConfirmation(
            command,
            `Install package: ${packageName} using ${manager}`
        );
    }

    /**
     * Log an audit entry
     */
    private async logAuditEntry(entry: AuditLogEntry): Promise<void> {
        try {
            const logDir = join(homedir(), ".amfbot");
            await mkdir(logDir, { recursive: true });

            const logLine = JSON.stringify({
                ...entry,
                timestamp: entry.timestamp.toISOString(),
            }) + "\n";

            await appendFile(this.config.logPath, logLine);
            this.emit("audit-logged", entry);
        } catch (error) {
            this.emit("audit-error", error);
        }
    }

    /**
     * Get the audit log path
     */
    getAuditLogPath(): string {
        return this.config.logPath;
    }

    /**
     * Check remaining session time
     */
    getRemainingSessionTime(): number {
        if (!this.sessionExpiry) return 0;
        const remaining = this.sessionExpiry.getTime() - Date.now();
        return Math.max(0, remaining);
    }
}

export default RootAccess;
