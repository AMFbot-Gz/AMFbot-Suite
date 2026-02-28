import fs from "fs-extra";
import path from "path";
import chalk from "chalk";

/**
 * Sovereign MCP Scanner
 * v2.6 "Elite" Auto-discovery Service.
 */
export class MCPScanner {
    private static standardPaths = [
        path.join(process.env.HOME || "", ".mcp"),
        path.join(process.env.HOME || "", "Library/Application Support/mcp"), // macOS
        "./mcp-servers"
    ];

    /**
     * Scans for local MCP server configurations
     */
    static async scan(): Promise<string[]> {
        console.log(chalk.dim("🌀 MCP_HUB: Scanning for server configurations..."));
        const foundServers: string[] = [];

        for (const dir of this.standardPaths) {
            try {
                if (await fs.pathExists(dir)) {
                    const files = await fs.readdir(dir);
                    const configs = files.filter(f => f.endsWith(".json"));
                    configs.forEach(c => foundServers.push(path.join(dir, c)));
                }
            } catch (e) {
                // Silently skip inaccessible dirs
            }
        }

        if (foundServers.length > 0) {
            console.log(chalk.green(`✅ MCP_HUB: Detected \${foundServers.length} servers.`));
        } else {
            console.log(chalk.yellow("⚠️ MCP_HUB: No local MCP servers detected."));
        }

        return foundServers;
    }
}
