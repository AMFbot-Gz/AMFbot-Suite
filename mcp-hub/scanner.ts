/**
 * AMFbot MCP Scanner
 *
 * Scans the user's system for potential MCP connections:
 * - Git repositories
 * - Google Drive folders
 * - Cloud credentials
 * - Database connections
 *
 * @license Apache-2.0
 */

import { glob } from "glob";
import { readFile, access } from "fs/promises";
import { homedir } from "os";
import { join, basename } from "path";

export interface MCPSuggestion {
    id: string;
    name: string;
    description: string;
    type: "filesystem" | "git" | "database" | "cloud" | "custom";
    installCommand: string;
    config: Record<string, unknown>;
    confidence: number; // 0-1
}

export interface ScanOptions {
    paths?: string[];
    includeHidden?: boolean;
    maxDepth?: number;
}

const CLOUD_CREDENTIALS_PATHS: Record<string, { name: string; type: string }> = {
    "~/.config/gcloud/application_default_credentials.json": { name: "Google Cloud", type: "gcloud" },
    "~/.aws/credentials": { name: "AWS", type: "aws" },
    "~/.azure/config": { name: "Azure", type: "azure" },
    "~/.config/gh/hosts.yml": { name: "GitHub CLI", type: "github" },
};

const KNOWN_DRIVE_PATHS = [
    "~/Google Drive",
    "~/Library/CloudStorage/GoogleDrive-*",
    "~/Dropbox",
    "~/OneDrive",
    "~/iCloud Drive",
];

export class MCPScanner {
    private homePath: string;

    constructor() {
        this.homePath = homedir();
    }

    /**
     * Scan for all potential MCP connections
     */
    async scan(options: ScanOptions = {}): Promise<MCPSuggestion[]> {
        const suggestions: MCPSuggestion[] = [];

        // Run scans in parallel
        const [gitRepos, cloudDrives, cloudCredentials] = await Promise.all([
            this.scanGitRepositories(options),
            this.scanCloudDrives(),
            this.scanCloudCredentials(),
        ]);

        suggestions.push(...gitRepos);
        suggestions.push(...cloudDrives);
        suggestions.push(...cloudCredentials);

        // Sort by confidence
        suggestions.sort((a, b) => b.confidence - a.confidence);

        return suggestions;
    }

    /**
     * Scan for Git repositories
     */
    private async scanGitRepositories(options: ScanOptions): Promise<MCPSuggestion[]> {
        const suggestions: MCPSuggestion[] = [];
        const searchPaths = options.paths || [
            join(this.homePath, "Developer"),
            join(this.homePath, "Projects"),
            join(this.homePath, "Code"),
            join(this.homePath, "repos"),
            join(this.homePath, "git"),
            join(this.homePath, "src"),
            join(this.homePath, "workspace"),
        ];

        for (const searchPath of searchPaths) {
            try {
                const gitDirs = await glob("**/.git", {
                    cwd: searchPath,
                    maxDepth: options.maxDepth || 3,
                    ignore: ["**/node_modules/**", "**/vendor/**"],
                    dot: true,
                });

                for (const gitDir of gitDirs) {
                    const repoPath = join(searchPath, gitDir.replace("/.git", ""));
                    const repoName = basename(repoPath);

                    suggestions.push({
                        id: `git-${repoName}-${Buffer.from(repoPath).toString("base64").slice(0, 8)}`,
                        name: `Git: ${repoName}`,
                        description: `Git repository at ${repoPath}`,
                        type: "git",
                        installCommand: "uvx mcp-server-git",
                        config: {
                            repository: repoPath,
                        },
                        confidence: 0.8,
                    });
                }
            } catch {
                // Path doesn't exist, skip
            }
        }

        return suggestions;
    }

    /**
     * Scan for cloud storage drives
     */
    private async scanCloudDrives(): Promise<MCPSuggestion[]> {
        const suggestions: MCPSuggestion[] = [];

        for (const drivePath of KNOWN_DRIVE_PATHS) {
            const expandedPath = drivePath.replace("~", this.homePath);

            try {
                // Handle glob patterns
                const matches = await glob(expandedPath);

                for (const match of matches) {
                    await access(match);

                    const driveName = basename(match);
                    let driveType: string;

                    if (match.includes("GoogleDrive") || match.includes("Google Drive")) {
                        driveType = "Google Drive";
                    } else if (match.includes("Dropbox")) {
                        driveType = "Dropbox";
                    } else if (match.includes("OneDrive")) {
                        driveType = "OneDrive";
                    } else if (match.includes("iCloud")) {
                        driveType = "iCloud";
                    } else {
                        driveType = "Cloud Storage";
                    }

                    suggestions.push({
                        id: `filesystem-${Buffer.from(match).toString("base64").slice(0, 8)}`,
                        name: `${driveType}: ${driveName}`,
                        description: `${driveType} folder at ${match}`,
                        type: "filesystem",
                        installCommand: "npx -y @modelcontextprotocol/server-filesystem",
                        config: {
                            allowedDirectories: [match],
                        },
                        confidence: 0.9,
                    });
                }
            } catch {
                // Path doesn't exist
            }
        }

        return suggestions;
    }

    /**
     * Scan for cloud credentials
     */
    private async scanCloudCredentials(): Promise<MCPSuggestion[]> {
        const suggestions: MCPSuggestion[] = [];

        for (const [credPath, info] of Object.entries(CLOUD_CREDENTIALS_PATHS)) {
            const expandedPath = credPath.replace("~", this.homePath);

            try {
                await access(expandedPath);

                // Credential file exists
                if (info.type === "github") {
                    suggestions.push({
                        id: "github-mcp",
                        name: "GitHub",
                        description: "Connect to GitHub repositories and issues",
                        type: "cloud",
                        installCommand: "npx -y @modelcontextprotocol/server-github",
                        config: {
                            // Token should be set via env
                        },
                        confidence: 0.95,
                    });
                } else if (info.type === "gcloud") {
                    suggestions.push({
                        id: "gcloud-mcp",
                        name: "Google Cloud",
                        description: "Connect to Google Cloud services",
                        type: "cloud",
                        installCommand: "npx -y @anthropic/gcp-mcp-server",
                        config: {},
                        confidence: 0.85,
                    });

                    // Also suggest Google Drive
                    suggestions.push({
                        id: "gdrive-mcp",
                        name: "Google Drive",
                        description: "Access Google Drive files",
                        type: "cloud",
                        installCommand: "npx -y @anthropic/gdrive-mcp-server",
                        config: {},
                        confidence: 0.85,
                    });
                }
            } catch {
                // Credential file doesn't exist
            }
        }

        return suggestions;
    }

    /**
     * Scan for database connections
     */
    async scanDatabases(): Promise<MCPSuggestion[]> {
        const suggestions: MCPSuggestion[] = [];

        // Check for common database config files
        const dbConfigPaths = [
            join(this.homePath, ".pgpass"),
            join(this.homePath, ".my.cnf"),
            join(this.homePath, ".mongodb"),
        ];

        for (const configPath of dbConfigPaths) {
            try {
                await access(configPath);

                if (configPath.includes(".pgpass")) {
                    suggestions.push({
                        id: "postgres-mcp",
                        name: "PostgreSQL",
                        description: "Connect to PostgreSQL databases",
                        type: "database",
                        installCommand: "npx -y @modelcontextprotocol/server-postgres",
                        config: {
                            // Connection string should be configured
                        },
                        confidence: 0.7,
                    });
                }
            } catch {
                // Config doesn't exist
            }
        }

        // Check for running database services
        try {
            const { execa } = await import("execa");

            // Check PostgreSQL
            try {
                await execa("pg_isready", [], { reject: true });
                suggestions.push({
                    id: "postgres-local-mcp",
                    name: "PostgreSQL (Local)",
                    description: "Local PostgreSQL server detected",
                    type: "database",
                    installCommand: "npx -y @modelcontextprotocol/server-postgres",
                    config: {
                        connectionString: "postgresql://localhost/postgres",
                    },
                    confidence: 0.75,
                });
            } catch {
                // PostgreSQL not running
            }
        } catch {
            // execa not available
        }

        return suggestions;
    }

    /**
     * Generate MCP config entry for a suggestion
     */
    generateConfigEntry(suggestion: MCPSuggestion): Record<string, unknown> {
        const isNpx = suggestion.installCommand.startsWith("npx");

        if (isNpx) {
            const parts = suggestion.installCommand.split(" ");
            const packageName = parts[parts.length - 1];

            return {
                [suggestion.id]: {
                    command: "npx",
                    args: ["-y", packageName, ...Object.values(suggestion.config).map(String)],
                },
            };
        } else {
            // uvx command
            const parts = suggestion.installCommand.split(" ");
            const packageName = parts[parts.length - 1];

            return {
                [suggestion.id]: {
                    command: "uvx",
                    args: [packageName, ...Object.entries(suggestion.config).flatMap(([k, v]) => [`--${k}`, String(v)])],
                },
            };
        }
    }
}

export default MCPScanner;
