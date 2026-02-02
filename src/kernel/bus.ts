import { env } from "../config/env";
import chalk from "chalk";

/**
 * Sovereign Event Bus (SSE)
 * Low-latency delivery (<150ms target)
 */
export class SSEBus {
    /**
     * Wraps an async generator into an SSE-compatible stream
     */
    async *streamInference(generator: AsyncGenerator<string>): AsyncGenerator<string> {
        console.log(chalk.dim("📡 SSE: Stream opening..."));

        for await (const chunk of generator) {
            // Format as SSE data
            yield `data: \${JSON.stringify({ chunk, timestamp: Date.now() })}\n\n`;
        }

        yield "event: end\ndata: [EOI]\n\n";
        console.log(chalk.dim("📡 SSE: Stream finalized."));
    }
}
