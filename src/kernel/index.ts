import { EventEmitter } from "events";
import { env } from "../config/env";
import chalk from "chalk";

/**
 * AMF-OS Sovereign Elite Kernel
 * Event-Driven Core using Parallel Swarms (Workers)
 */
export class SovereignKernel extends EventEmitter {
    private workers: Map<string, Worker> = new Map();
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
        // In a full implementation, this finds an available worker 
        // or spawns a dedicated one for the task
    }

    private spawnWorker(id: string, path: string) {
        try {
            // Bun.Worker is zero-overhead for swarm orchestration
            const worker = new Worker(path);
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
            // Trigger atomic rollback if critical
        });
    }
}
