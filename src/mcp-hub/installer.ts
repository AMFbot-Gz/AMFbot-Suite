/**
 * AMFbot MCP Installer
 *
 * Manages installation and configuration of MCP servers:
 * - Auto-install via npx/uvx
 * - Dynamic config generation
 * - Self-registration for new custom servers
 *
 * @license Apache-2.0
 */

import { readFile, writeFile, mkdir, access } from "fs/promises";
import { join } from "path";
import { homedir } from "os";
import { EventEmitter } from "events";
import { execa } from "execa";

export interface MCPServerConfig {
    command: string;
    args: string[];
    env?: Record<string, string>;
}

export interface MCPConfig {
    mcpServers: Record<string, MCPServerConfig>;
}

export interface InstalledServer {
    id: string;
    name: string;
    type: "npx" | "uvx" | "custom";
    command: string;
    args: string[];
    enabled: boolean;
}

// Pre-defined MCP servers that can be installed
const AVAILABLE_SERVERS: Record<string, { name: string; command: string; args: string[]; type: "npx" | "uvx" }> = {
    filesystem: {
        name: "Filesystem",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-filesystem"],
        type: "npx",
    },
    git: {
        name: "Git",
        command: "uvx",
        args: ["mcp-server-git"],
        type: "uvx",
    },
    memory: {
        name: "Memory",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-memory"],
        type: "npx",
    },
    github: {
        name: "GitHub",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        type: "npx",
    },
    fetch: {
        name: "Fetch",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-fetch"],
        type: "npx",
    },
    time: {
        name: "Time",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-time"],
        type: "npx",
    },
    sequentialthinking: {
        name: "Sequential Thinking",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-sequentialthinking"],
        type: "npx",
    },
    postgres: {
        name: "PostgreSQL",
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-postgres"],
        type: "npx",
    },
    slack: {
        name: "Slack",
        command: "npx",
        args: ["-y", "@anthropic/slack-mcp-server"],
        type: "npx",
    },
    gdrive: {
        name: "Google Drive",
        command: "npx",
        args: ["-y", "@anthropic/gdrive-mcp-server"],
        type: "npx",
    },
};

export class MCPInstaller extends EventEmitter {
    private configPath: string;
    private customServersPath: string;

    constructor() {
        super();
        const amfbotDir = join(homedir(), ".amfbot");
        this.configPath = join(amfbotDir, "mcp-config.json");
        this.customServersPath = join(amfbotDir, "custom_servers");
    }

    /**
     * Get the config file path
     */
    getConfigPath(): string {
        return this.configPath;
    }

    /**
     * Load MCP configuration
     */
    async loadConfig(): Promise<MCPConfig> {
        try {
            const content = await readFile(this.configPath, "utf-8");
            return JSON.parse(content) as MCPConfig;
        } catch {
            // Return empty config if file doesn't exist
            return { mcpServers: {} };
        }
    }

    /**
     * Save MCP configuration
     */
    async saveConfig(config: MCPConfig): Promise<void> {
        const dir = join(homedir(), ".amfbot");
        await mkdir(dir, { recursive: true });
        await writeFile(this.configPath, JSON.stringify(config, null, 2));
        this.emit("config-saved", config);
    }

    /**
     * Install an MCP server
     */
    async install(serverId: string, customConfig?: Partial<MCPServerConfig>): Promise<void> {
        const serverDef = AVAILABLE_SERVERS[serverId];

        if (!serverDef && !customConfig) {
            throw new Error(`Unknown server: ${serverId}. Use customConfig for custom servers.`);
        }

        this.emit("install-start", { serverId });

        // Load existing config
        const config = await this.loadConfig();

        // Add server to config
        if (serverDef) {
            config.mcpServers[serverId] = {
                command: serverDef.command,
                args: [...serverDef.args, ...(customConfig?.args || [])],
                env: customConfig?.env,
            };
        } else if (customConfig) {
            config.mcpServers[serverId] = {
                command: customConfig.command!,
                args: customConfig.args || [],
                env: customConfig.env,
            };
        }

        // Verify the server works
        try {
            const serverConfig = config.mcpServers[serverId];
            await execa(serverConfig.command, [...serverConfig.args, "--help"], {
                timeout: 10000,
                reject: false,
            });
        } catch (error) {
            this.emit("install-warning", { serverId, message: "Could not verify server" });
        }

        // Save updated config
        await this.saveConfig(config);

        this.emit("install-complete", { serverId });
    }

    /**
     * Uninstall an MCP server
     */
    async uninstall(serverId: string): Promise<void> {
        const config = await this.loadConfig();

        if (!config.mcpServers[serverId]) {
            throw new Error(`Server not installed: ${serverId}`);
        }

        delete config.mcpServers[serverId];
        await this.saveConfig(config);

        this.emit("uninstall-complete", { serverId });
    }

    /**
     * List installed servers
     */
    async listInstalled(): Promise<InstalledServer[]> {
        const config = await this.loadConfig();
        const servers: InstalledServer[] = [];

        for (const [id, serverConfig] of Object.entries(config.mcpServers)) {
            const knownServer = AVAILABLE_SERVERS[id];

            servers.push({
                id,
                name: knownServer?.name || id,
                type: knownServer?.type || "custom",
                command: serverConfig.command,
                args: serverConfig.args,
                enabled: true,
            });
        }

        return servers;
    }

    /**
     * List available servers that can be installed
     */
    listAvailable(): Array<{ id: string; name: string; type: string }> {
        return Object.entries(AVAILABLE_SERVERS).map(([id, server]) => ({
            id,
            name: server.name,
            type: server.type,
        }));
    }

    /**
     * Create a custom MCP server
     */
    async createCustomServer(
        serverId: string,
        code: string,
        metadata: { name: string; description: string }
    ): Promise<void> {
        // Create custom servers directory
        await mkdir(this.customServersPath, { recursive: true });

        // Write the server code
        const serverPath = join(this.customServersPath, `${serverId}.py`);
        await writeFile(serverPath, code);

        // Register as MCP server
        await this.install(serverId, {
            command: "python",
            args: [serverPath],
        });

        // Write metadata
        const metaPath = join(this.customServersPath, `${serverId}.json`);
        await writeFile(metaPath, JSON.stringify(metadata, null, 2));

        this.emit("custom-server-created", { serverId, path: serverPath });
    }

    /**
     * List custom servers created by AMFbot
     */
    async listCustomServers(): Promise<Array<{ id: string; name: string; path: string }>> {
        const servers: Array<{ id: string; name: string; path: string }> = [];

        try {
            await access(this.customServersPath);

            const { glob } = await import("glob");
            const files = await glob("*.json", { cwd: this.customServersPath });

            for (const file of files) {
                const id = file.replace(".json", "");
                const metaPath = join(this.customServersPath, file);
                const meta = JSON.parse(await readFile(metaPath, "utf-8"));

                servers.push({
                    id,
                    name: meta.name,
                    path: join(this.customServersPath, `${id}.py`),
                });
            }
        } catch {
            // Directory doesn't exist yet
        }

        return servers;
    }

    /**
     * Generate config for Claude Desktop or other MCP clients
     */
    async exportForClient(client: "claude" | "amfbot"): Promise<string> {
        const config = await this.loadConfig();

        if (client === "claude") {
            return JSON.stringify(config, null, 2);
        }

        // AMFbot format (same for now, but could be extended)
        return JSON.stringify(config, null, 2);
    }

    /**
     * Import config from another MCP client
     */
    async importFromClient(configJson: string): Promise<void> {
        const importedConfig = JSON.parse(configJson) as MCPConfig;

        // Merge with existing config
        const currentConfig = await this.loadConfig();

        for (const [id, server] of Object.entries(importedConfig.mcpServers)) {
            currentConfig.mcpServers[id] = server;
        }

        await this.saveConfig(currentConfig);
        this.emit("config-imported", { count: Object.keys(importedConfig.mcpServers).length });
    }
}

export default MCPInstaller;
