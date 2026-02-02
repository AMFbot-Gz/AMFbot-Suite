import { EventEmitter } from "events";
import { env } from "../config/env.js";
import chalk from "chalk";

/**
 * AMF-OS Sovereign Elite Kernel
 * Event-Driven Core using Parallel Swarms (Workers)
 */
export class SovereignKernel extends EventEmitter {
    private workers: Map<string, any> = new Map();
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

        this.emit("kernel-ready");
        console.log(chalk.green("🌀 KERNEL: Swarm synchronized."));
    }

    /**
     * Dispatch task to the swarm
     */
    dispatch(taskId: string, payload: any) {
        this.emit("task-dispatched", { taskId, payload });
    }

    private spawnWorker(id: string, path: string) {
        try {
            // Bun.Worker supports both string paths and URLs
            const worker = new Worker(new URL("../../" + path, import.meta.url).href);
            this.workers.set(id, worker);

            worker.addEventListener("message", (event) => {
                this.emit(`worker-msg:\${id}`, event.data);
            });

            worker.addEventListener("error", (err) => {
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
