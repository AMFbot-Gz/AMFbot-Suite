/**
 * AMFbot Core Agent Runtime
 *
 * The central agent runtime that orchestrates all AMFbot capabilities:
 * - Session management
 * - Tool execution
 * - LLM integration via Ollama
 * - Event handling
 *
 * @license Apache-2.0
 */

import { Ollama } from "ollama";
import { EventEmitter } from "events";
import { HardwareDetector, HardwareCapabilities } from "./hardware-detector.js";
import { RootAccess } from "./root-access.js";
import { SessionStore } from "./session-store.js";

export interface AgentConfig {
    model: string;
    ollamaHost?: string;
    systemPrompt?: string;
    tools?: AgentTool[];
    maxTokens?: number;
    temperature?: number;
}

export interface AgentTool {
    name: string;
    description: string;
    parameters: Record<string, ToolParameter>;
    handler: (params: Record<string, unknown>) => Promise<unknown>;
}

export interface ToolParameter {
    type: "string" | "number" | "boolean" | "array" | "object";
    description: string;
    required?: boolean;
    default?: unknown;
}

export interface Message {
    role: "user" | "assistant" | "system" | "tool";
    content: string;
    toolCalls?: ToolCall[];
    toolResults?: ToolResult[];
}

export interface ToolCall {
    id: string;
    name: string;
    arguments: Record<string, unknown>;
}

export interface ToolResult {
    callId: string;
    result: unknown;
    error?: string;
}

export interface Session {
    id: string;
    messages: Message[];
    createdAt: Date;
    lastActiveAt: Date;
    metadata: Record<string, unknown>;
}

const DEFAULT_SYSTEM_PROMPT = `You are AMFbot, a powerful sovereign AI assistant with full system control capabilities.

You have access to the following abilities:
- Execute system commands (with user confirmation for sudo operations)
- Generate images using Flux.1
- Generate videos using LTX-Video
- Manage files and directories
- Connect to external services via MCP

Always be helpful, precise, and transparent about your actions. When performing system operations, explain what you're about to do before executing.

IMPORTANT: For any operation that requires elevated privileges (sudo), you MUST request explicit user confirmation first.`;

export class Agent extends EventEmitter {
    private ollama: Ollama;
    private config: AgentConfig;
    private sessions: Map<string, Session> = new Map();
    private tools: Map<string, AgentTool> = new Map();
    private hardware: HardwareCapabilities | null = null;
    private rootAccess: RootAccess;
    private sessionStore: SessionStore;

    constructor(config: AgentConfig) {
        super();
        this.config = {
            model: config.model || "llama3.2",
            ollamaHost: config.ollamaHost || "http://localhost:11434",
            systemPrompt: config.systemPrompt || DEFAULT_SYSTEM_PROMPT,
            maxTokens: config.maxTokens || 4096,
            temperature: config.temperature || 0.7,
            tools: config.tools || [],
        };

        this.ollama = new Ollama({ host: this.config.ollamaHost });
        this.rootAccess = new RootAccess();
        this.sessionStore = new SessionStore();

        // Register provided tools
        for (const tool of this.config.tools || []) {
            this.registerTool(tool);
        }

        // Register built-in tools
        this.registerBuiltInTools();
    }

    /**
     * Initialize the agent and detect hardware capabilities
     */
    async initialize(): Promise<void> {
        this.emit("initializing");

        // Detect hardware
        const detector = new HardwareDetector();
        this.hardware = await detector.detect();

        this.emit("hardware-detected", this.hardware);

        // Verify Ollama connection
        try {
            await this.ollama.list();
            this.emit("ollama-connected");
        } catch (error) {
            this.emit("ollama-error", error);
            throw new Error(
                `Failed to connect to Ollama at ${this.config.ollamaHost}: ${error}`
            );
        }

        // Pull model if not available
        const models = await this.ollama.list();
        const hasModel = models.models.some((m) =>
            m.name.startsWith(this.config.model)
        );

        if (!hasModel) {
            this.emit("model-pulling", this.config.model);
            await this.ollama.pull({ model: this.config.model });
            this.emit("model-pulled", this.config.model);
        }

        this.emit("initialized", { hardware: this.hardware });
    }

    /**
     * Create a new session
     */
    createSession(metadata: Record<string, unknown> = {}): Session {
        const session: Session = {
            id: crypto.randomUUID(),
            messages: [
                {
                    role: "system",
                    content: this.config.systemPrompt || DEFAULT_SYSTEM_PROMPT,
                },
            ],
            createdAt: new Date(),
            lastActiveAt: new Date(),
            metadata,
        };

        this.sessions.set(session.id, session);
        this.sessionStore.saveSession(session); // Persist
        this.emit("session-created", session);

        return session;
    }

    /**
     * Get an existing session
     */
    async getSession(sessionId: string): Promise<Session | undefined> {
        // Try memory first
        if (this.sessions.has(sessionId)) {
            return this.sessions.get(sessionId);
        }
        // Try disk
        const session = await this.sessionStore.getSession(sessionId);
        if (session) {
            this.sessions.set(sessionId, session);
        }
        return session;
    }

    /**
     * Send a message and get a response
     */
    async chat(
        sessionId: string,
        userMessage: string
    ): Promise<AsyncGenerator<string, void, unknown>> {
        const session = await this.getSession(sessionId); // Await because getSession is async now
        if (!session) {
            throw new Error(`Session ${sessionId} not found`);
        }

        // Add user message
        session.messages.push({ role: "user", content: userMessage });
        session.lastActiveAt = new Date();

        // Generate response
        const response = await this.ollama.chat({
            model: this.config.model,
            messages: session.messages.map((m) => ({
                role: m.role as "user" | "assistant" | "system",
                content: m.content,
            })),
            stream: true,
            options: {
                temperature: this.config.temperature,
                num_predict: this.config.maxTokens,
            },
        });

        const self = this;

        const validSession = session;
        async function* streamResponse(): AsyncGenerator<string, void, unknown> {
            let fullContent = "";

            for await (const chunk of response) {
                fullContent += chunk.message.content;
                yield chunk.message.content;
            }

            // Store complete response
            validSession.messages.push({ role: "assistant", content: fullContent });
            await self.sessionStore.saveSession(validSession);
            self.emit("message-complete", { sessionId, content: fullContent });
        }

        return streamResponse();
    }

    /**
     * Execute a tool call
     */
    async executeTool(
        toolName: string,
        params: Record<string, unknown>
    ): Promise<unknown> {
        const tool = this.tools.get(toolName);
        if (!tool) {
            throw new Error(`Tool ${toolName} not found`);
        }

        this.emit("tool-executing", { name: toolName, params });

        try {
            const result = await tool.handler(params);
            this.emit("tool-complete", { name: toolName, result });
            return result;
        } catch (error) {
            this.emit("tool-error", { name: toolName, error });
            throw error;
        }
    }

    /**
     * Register a new tool
     */
    registerTool(tool: AgentTool): void {
        this.tools.set(tool.name, tool);
        this.emit("tool-registered", tool.name);
    }

    /**
     * Get hardware capabilities
     */
    getHardwareCapabilities(): HardwareCapabilities | null {
        return this.hardware;
    }

    /**
     * Get root access module for privileged operations
     */
    getRootAccess(): RootAccess {
        return this.rootAccess;
    }

    /**
     * Register built-in tools
     */
    private registerBuiltInTools(): void {
        // Shell command execution
        this.registerTool({
            name: "execute_command",
            description:
                "Execute a shell command. For sudo commands, user confirmation is required.",
            parameters: {
                command: {
                    type: "string",
                    description: "The shell command to execute",
                    required: true,
                },
                cwd: {
                    type: "string",
                    description: "Working directory for the command",
                    required: false,
                },
                requiresSudo: {
                    type: "boolean",
                    description: "Whether this command requires sudo",
                    required: false,
                    default: false,
                },
            },
            handler: async (params) => {
                const { command, cwd, requiresSudo } = params as {
                    command: string;
                    cwd?: string;
                    requiresSudo?: boolean;
                };

                if (requiresSudo) {
                    return this.rootAccess.executeWithConfirmation(
                        command,
                        `Execute sudo command: ${command}`
                    );
                }

                const { execa } = await import("execa");
                const result = await execa(command, {
                    shell: true,
                    cwd: cwd || process.cwd(),
                });

                return {
                    stdout: result.stdout,
                    stderr: result.stderr,
                    exitCode: result.exitCode,
                };
            },
        });

        // File system operations
        this.registerTool({
            name: "read_file",
            description: "Read the contents of a file",
            parameters: {
                path: {
                    type: "string",
                    description: "Path to the file to read",
                    required: true,
                },
            },
            handler: async (params) => {
                const { readFile } = await import("fs/promises");
                const content = await readFile(params.path as string, "utf-8");
                return { content };
            },
        });

        this.registerTool({
            name: "write_file",
            description: "Write content to a file",
            parameters: {
                path: {
                    type: "string",
                    description: "Path to the file to write",
                    required: true,
                },
                content: {
                    type: "string",
                    description: "Content to write to the file",
                    required: true,
                },
            },
            handler: async (params) => {
                const { writeFile, mkdir } = await import("fs/promises");
                const { dirname } = await import("path");

                const filePath = params.path as string;
                await mkdir(dirname(filePath), { recursive: true });
                await writeFile(filePath, params.content as string, "utf-8");

                return { success: true, path: filePath };
            },
        });

        // System info
        this.registerTool({
            name: "get_system_info",
            description: "Get information about the current system",
            parameters: {},
            handler: async () => {
                return {
                    hardware: this.hardware,
                    platform: process.platform,
                    arch: process.arch,
                    nodeVersion: process.version,
                };
            },
        });
    }

    /**
     * Shutdown the agent
     */
    async shutdown(): Promise<void> {
        this.emit("shutting-down");
        this.sessions.clear();
        this.emit("shutdown");
    }
}

export default Agent;
