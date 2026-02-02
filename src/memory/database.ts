import * as lancedb from "vectordb";
import { env } from "../config/env";
import path from "path";

export class MemoryStore {
    private dbPath = path.join(process.env.HOME || ".", ".amf-os", "lancedb");

    async init() {
        const db = await lancedb.connect(this.dbPath);
        return db;
    }

    /**
     * Store a successful command for tactical knowledge
     */
    async rememberCommand(command: string, context: string, success: boolean) {
        const db = await this.init();
        const tableNames = await db.tableNames();

        if (!tableNames.includes("tactical_knowledge")) {
            await db.createTable("tactical_knowledge", [
                { vector: new Array(1536).fill(0), command, context, success, timestamp: Date.now() }
            ]);
        }

        const table = await db.openTable("tactical_knowledge");
        await table.add([{
            vector: new Array(1536).fill(0), // Placeholder for real embeddings
            command,
            context,
            success,
            timestamp: Date.now()
        }]);
    }
}
