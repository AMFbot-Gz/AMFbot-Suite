import { EventEmitter } from "events";
import { SovereignKernel } from "../kernel/index.js";
import { SovereignOrchestrator } from "./orchestrator.js";
import { HardwareDetector, HardwareCapabilities } from "./hardware-detector.js";
import chalk from "chalk";

/**
 * AMF-OS SOVEREIGN AGENT
 * The professional façade for the entire system.
 */
export class AMFAgent extends EventEmitter {
    private kernel: SovereignKernel;
    private orchestrator: SovereignOrchestrator;
    private detector = new HardwareDetector();
    private capabilities: HardwareCapabilities | null = null;
    private sessions: Map<string, any> = new Map();

    constructor() {
        super();
        this.kernel = new SovereignKernel();
        this.orchestrator = new SovereignOrchestrator();
    }

    /**
     * INITIALIZE
     * Detects hardware, boots kernel, and prepares orchestrator.
     */
    async initialize() {
        console.log(chalk.cyan("🛸 AGENT: Initializing Sovereign System..."));

        // 1. Hardware Detection
        this.capabilities = await this.detector.detect();
        this.emit("hardware-detected", this.capabilities);

        // 2. Boot Kernel
        await this.kernel.boot();
        this.emit("kernel-ready");

        console.log(chalk.green("✅ AGENT: Sovereign System Ready."));
    }

    /**
     * GET HARDWARE CAPABILITIES
     */
    getHardwareCapabilities(): HardwareCapabilities | null {
        return this.capabilities;
    }

    /**
     * SESSIONS
     */
    createSession(metadata: any = {}) {
        const id = Math.random().toString(36).substring(7);
        const session = { id, createdAt: new Date(), metadata };
        this.sessions.set(id, session);
        return session;
    }

    async listSessions() {
        return Array.from(this.sessions.values());
    }

    /**
     * CHAT (Sovereign Loop)
     */
    async *chat(sessionId: string, input: string): AsyncGenerator<string> {
        console.log(chalk.dim(`📡 AGENT: Session [\${sessionId}] Instruction: "\${input.slice(0, 50)}..."`));
        yield* this.orchestrator.runSovereignLoop(input);
    }

    /**
     * SHUTDOWN
     */
    async shutdown() {
        console.log(chalk.yellow("🛑 AGENT: Initiating graceful shutdown..."));
    }
}

export { AMFAgent as Agent };
