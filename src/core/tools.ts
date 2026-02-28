export enum PermissionLevel {
    USER = 0,
    ADMIN = 1,
    ROOT = 2
}

export interface Tool {
    name: string;
    description: string;
    executable: string;
    level: PermissionLevel;
}

/**
 * AMF-OS Tool Registry
 * Explicit definition of what the agent can touch.
 */
export class ToolRegistry {
    private tools: Map<string, Tool> = new Map();

    constructor() {
        this.registerDefaultTools();
    }

    register(tool: Tool) {
        this.tools.set(tool.name, tool);
    }

    private registerDefaultTools() {
        this.register({
            name: "fs_read",
            description: "Read files within project workspace",
            executable: "cat",
            level: PermissionLevel.USER
        });

        this.register({
            name: "shell_exec",
            description: "Execute safe shell commands",
            executable: "bash",
            level: PermissionLevel.ADMIN
        });

        this.register({
            name: "git_rollback",
            description: "Atomic system rollback",
            executable: "git",
            level: PermissionLevel.ADMIN
        });
    }

    getTool(name: string): Tool | undefined {
        return this.tools.get(name);
    }

    isAllowed(toolName: string, userLevel: PermissionLevel): boolean {
        const tool = this.tools.get(toolName);
        if (!tool) return false;
        return userLevel >= tool.level;
    }
}
