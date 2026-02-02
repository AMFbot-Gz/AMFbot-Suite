import { expect, test, describe } from "bun:test";
import { SovereignKernel } from "../kernel/index.js";

describe("SovereignKernel", () => {
    test("should initialize and emit kernel-ready", async () => {
        const kernel = new SovereignKernel();
        let ready = false;

        kernel.on("kernel-ready", () => {
            ready = true;
        });

        await kernel.boot();
        expect(ready).toBe(true);
    });

    test("should track running status", async () => {
        const kernel = new SovereignKernel();
        // Accessing private for test
        expect((kernel as any).isRunning).toBe(false);
        await kernel.boot();
        expect((kernel as any).isRunning).toBe(true);
    });
});
