import { EventEmitter } from "events";
import { HeartbeatService } from "./heartbeat.js";
import chalk from "chalk";

/**
 * AMF-OS Sovereign Elite Kernel
 * Event-Driven Core using Parallel Swarms (Workers)
 */
export class SovereignKernel extends EventEmitter {
    private workers: Map<string, any> = new Map();
    private heartbeat = new HeartbeatService();
    private isRunning = false;

    constructor() {
        super();
        this.setupErrorHandlers();
    }

    /**
     * Initialize the Micro-Kernel swarm
     */
    async boot() {
        console.log(chalk.bold.cyan("\n🌀 KERNEL: Initializing Sovereign Swarm..."));
        this.isRunning = true;

        // Spawn core monitoring/sentinel worker
        this.spawnWorker("sentinel", "./src/sentinel/worker.ts");

        // Start Multi-node Heartbeat
        await this.heartbeat.start();

        this.emit("kernel-ready");
        console.log(chalk.green("🌀 KERNEL: Swarm synchronized."));
    }

    /**
     * Dispatch task to the swarm
     */
    dispatch(taskId: string, payload: any) {
        this.emit("task-dispatched", { taskId, payload });
    }

    /**
     * Check if kernel is running
     */
    status() {
        return this.isRunning;
    }

    private spawnWorker(id: string, path: string) {
        try {
            // Bun.Worker supports both string paths and URLs
            // Use 'any' to avoid type conflict if environment differs
            const worker = new (globalThis as any).Worker(new URL("../../" + path, import.meta.url).href);
            this.workers.set(id, worker);

            worker.addEventListener("message", (event: any) => {
                this.emit(`worker-msg:\${id}`, event.data);
            });

            worker.addEventListener("error", (err: any) => {
                console.error(chalk.red(`🔥 KERNEL: Worker [\${id}] Failure:`), err);
                this.emit("kernel-panic", { id, error: err });
            });
        } catch (e) {
            console.error(chalk.red(`🔥 KERNEL: Failed to spawn worker [\${id}]:`), e);
        }
    }

    private setupErrorHandlers() {
        process.on("uncaughtException", (err) => {
            console.error(chalk.bgRed.white(" 🔥 KERNEL PANIC (UncaughtException) "), err);
        });
    }
}
