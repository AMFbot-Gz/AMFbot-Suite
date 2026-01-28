/**
 * AMFbot Hybrid API Client
 *
 * Implements hybrid mode:
 * - Anthropic Claude for complex reasoning and Computer Use
 * - Ollama (local) for simple chat and basic tasks
 * - Automatic routing based on task complexity
 *
 * Designed to switch to 100% local when Llama 3.2 Vision is supported
 *
 * @license Apache-2.0
 */

import { OllamaClient } from "./ollama-client.js";
import { EventEmitter } from "events";

export interface HybridConfig {
    /** Anthropic API key for Claude */
    anthropicApiKey?: string;
    /** Ollama host URL */
    ollamaHost?: string;
    /** Default local model */
    localModel?: string;
    /** Claude model for complex tasks */
    claudeModel?: string;
    /** Force local-only mode (no cloud APIs) */
    forceLocal?: boolean;
    /** Complexity threshold for routing (0-1) */
    complexityThreshold?: number;
}

export interface Message {
    role: "user" | "assistant" | "system";
    content: string;
}

export type TaskType =
    | "simple_chat"
    | "code_generation"
    | "computer_use"
    | "complex_reasoning"
    | "media_generation";

export interface RoutingDecision {
    provider: "anthropic" | "ollama";
    reason: string;
    taskType: TaskType;
}

// Keywords that indicate complex tasks requiring Claude
const COMPLEX_TASK_KEYWORDS = [
    "computer use",
    "control my",
    "click on",
    "open the app",
    "take a screenshot",
    "control the browser",
    "automate",
    "execute command",
    "run script",
    "complex analysis",
    "multi-step reasoning",
];

// Keywords that indicate simple tasks for local LLM
const SIMPLE_TASK_KEYWORDS = [
    "explain",
    "what is",
    "define",
    "summarize",
    "translate",
    "hello",
    "hi",
    "thanks",
    "help",
];

export class HybridAPIClient extends EventEmitter {
    private config: Required<HybridConfig>;
    private ollamaClient: OllamaClient;
    private anthropicAvailable: boolean = false;

    constructor(config: HybridConfig = {}) {
        super();

        this.config = {
            anthropicApiKey: config.anthropicApiKey || process.env.ANTHROPIC_API_KEY || "",
            ollamaHost: config.ollamaHost || "http://localhost:11434",
            localModel: config.localModel || "llama3.2",
            claudeModel: config.claudeModel || "claude-sonnet-4-20250514",
            forceLocal: config.forceLocal ?? false,
            complexityThreshold: config.complexityThreshold ?? 0.5,
        };

        this.ollamaClient = new OllamaClient({ host: this.config.ollamaHost });
        this.anthropicAvailable = !!this.config.anthropicApiKey && !this.config.forceLocal;

        if (this.config.forceLocal) {
            console.log("🏠 AMFbot running in 100% local mode");
        } else if (this.anthropicAvailable) {
            console.log("🔀 AMFbot running in hybrid mode (Anthropic + Ollama)");
        } else {
            console.log("🏠 AMFbot running with Ollama only (no Anthropic key)");
        }
    }

    /**
     * Route a request to the appropriate provider
     */
    routeRequest(messages: Message[]): RoutingDecision {
        // If forced local, always use Ollama
        if (this.config.forceLocal || !this.anthropicAvailable) {
            return {
                provider: "ollama",
                reason: this.config.forceLocal ? "Local mode enforced" : "Anthropic not configured",
                taskType: "simple_chat",
            };
        }

        // Analyze the latest user message
        const lastUserMessage = messages.filter((m) => m.role === "user").pop();
        if (!lastUserMessage) {
            return { provider: "ollama", reason: "No user message", taskType: "simple_chat" };
        }

        const content = lastUserMessage.content.toLowerCase();
        const taskType = this.classifyTask(content);

        // Route based on task type
        switch (taskType) {
            case "computer_use":
                return {
                    provider: "anthropic",
                    reason: "Computer Use requires Claude with tool support",
                    taskType,
                };

            case "complex_reasoning":
                return {
                    provider: "anthropic",
                    reason: "Complex multi-step reasoning benefits from Claude",
                    taskType,
                };

            case "code_generation":
                // Use Claude for complex code, Ollama for simple snippets
                if (content.length > 200 || content.includes("refactor") || content.includes("architect")) {
                    return {
                        provider: "anthropic",
                        reason: "Complex code task",
                        taskType,
                    };
                }
                return {
                    provider: "ollama",
                    reason: "Simple code task, using local model",
                    taskType,
                };

            case "media_generation":
                // Media generation is always local (via media-gen module)
                return {
                    provider: "ollama",
                    reason: "Media generation handled by local module",
                    taskType,
                };

            case "simple_chat":
            default:
                return {
                    provider: "ollama",
                    reason: "Simple chat task, using local model for privacy",
                    taskType,
                };
        }
    }

    /**
     * Classify the task type based on message content
     */
    private classifyTask(content: string): TaskType {
        // Check for computer use indicators
        if (COMPLEX_TASK_KEYWORDS.some((kw) => content.includes(kw))) {
            if (
                content.includes("click") ||
                content.includes("screenshot") ||
                content.includes("browser") ||
                content.includes("control")
            ) {
                return "computer_use";
            }
            return "complex_reasoning";
        }

        // Check for code generation
        if (
            content.includes("code") ||
            content.includes("function") ||
            content.includes("implement") ||
            content.includes("write a program") ||
            content.includes("debug")
        ) {
            return "code_generation";
        }

        // Check for media generation
        if (
            content.includes("generate image") ||
            content.includes("create image") ||
            content.includes("generate video") ||
            content.includes("create video") ||
            content.includes("draw") ||
            content.includes("design")
        ) {
            return "media_generation";
        }

        // Default to simple chat
        return "simple_chat";
    }

    /**
     * Chat with automatic routing
     */
    async chat(
        messages: Message[],
        options: { forceProvider?: "anthropic" | "ollama" } = {}
    ): Promise<AsyncGenerator<string, void, unknown>> {
        const routing = options.forceProvider
            ? { provider: options.forceProvider, reason: "Forced", taskType: "simple_chat" as TaskType }
            : this.routeRequest(messages);

        this.emit("routing-decision", routing);

        if (routing.provider === "anthropic" && this.anthropicAvailable) {
            return this.chatWithAnthropic(messages);
        }

        return this.chatWithOllama(messages);
    }

    /**
     * Chat with Ollama (local)
     */
    private async chatWithOllama(messages: Message[]): Promise<AsyncGenerator<string, void, unknown>> {
        this.emit("provider-selected", { provider: "ollama", model: this.config.localModel });

        return this.ollamaClient.chat({
            model: this.config.localModel,
            messages: messages.map((m) => ({
                role: m.role,
                content: m.content,
            })),
        });
    }

    /**
     * Chat with Anthropic Claude
     */
    private async chatWithAnthropic(messages: Message[]): Promise<AsyncGenerator<string, void, unknown>> {
        this.emit("provider-selected", { provider: "anthropic", model: this.config.claudeModel });

        // Dynamic import to avoid dependency if not used
        const response = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": this.config.anthropicApiKey,
                "anthropic-version": "2023-06-01",
            },
            body: JSON.stringify({
                model: this.config.claudeModel,
                max_tokens: 4096,
                messages: messages.filter((m) => m.role !== "system").map((m) => ({
                    role: m.role,
                    content: m.content,
                })),
                system: messages.find((m) => m.role === "system")?.content,
                stream: true,
            }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Anthropic API error: ${error}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        const self = this;

        async function* streamResponse(): AsyncGenerator<string, void, unknown> {
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.slice(6);
                        if (data === "[DONE]") continue;

                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.type === "content_block_delta" && parsed.delta?.text) {
                                yield parsed.delta.text;
                            }
                        } catch {
                            // Skip non-JSON lines
                        }
                    }
                }
            }

            self.emit("stream-complete", { provider: "anthropic" });
        }

        return streamResponse();
    }

    /**
     * Execute a Computer Use task (Claude only)
     */
    async executeComputerUse(task: string, tools: unknown[]): Promise<unknown> {
        if (!this.anthropicAvailable) {
            throw new Error("Computer Use requires Anthropic API key. Set ANTHROPIC_API_KEY environment variable.");
        }

        this.emit("computer-use-start", { task });

        const response = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": this.config.anthropicApiKey,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "computer-use-2024-10-22",
            },
            body: JSON.stringify({
                model: this.config.claudeModel,
                max_tokens: 4096,
                messages: [{ role: "user", content: task }],
                tools,
            }),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Computer Use error: ${error}`);
        }

        const result = await response.json();
        this.emit("computer-use-complete", { task, result });

        return result;
    }

    /**
     * Check if we're ready for 100% local mode
     */
    async checkLocalVisionSupport(): Promise<boolean> {
        // Check if Llama 3.2 Vision or similar is available
        try {
            const models = await this.ollamaClient.listModels();
            const visionModels = models.filter(
                (m) =>
                    m.name.includes("vision") ||
                    m.name.includes("llava") ||
                    m.name.includes("llama3.2")
            );

            if (visionModels.length > 0) {
                console.log("🎉 Local vision model detected! 100% local Computer Use may be possible.");
                return true;
            }
        } catch {
            // Ollama not available
        }

        return false;
    }

    /**
     * Switch to 100% local mode
     */
    enableLocalOnlyMode(): void {
        this.config.forceLocal = true;
        this.anthropicAvailable = false;
        this.emit("mode-changed", { mode: "local" });
        console.log("🏠 Switched to 100% local mode");
    }

    /**
     * Get current configuration
     */
    getConfig(): Readonly<HybridConfig> {
        return { ...this.config, anthropicApiKey: this.config.anthropicApiKey ? "[REDACTED]" : "" };
    }

    /**
     * Get the Ollama client for direct access
     */
    getOllamaClient(): OllamaClient {
        return this.ollamaClient;
    }
}

export default HybridAPIClient;
