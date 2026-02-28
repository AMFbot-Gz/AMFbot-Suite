export interface ISuccessPattern {
    vector_id: string;
    command_sequence: string[];
    system_state_before: object;
    exit_code: number;
    tokens_consumed: number;
    timestamp: string;
}

/**
 * Sovereign Memory Schema definitions
 */
export const MemorySchema = {
    success_pattern: [
        { name: "vector_id", type: "string" },
        { name: "command_sequence", type: "array" },
        { name: "exit_code", type: "int" },
        { name: "timestamp", type: "timestamp" }
    ]
};
