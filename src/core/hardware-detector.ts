/**
 * AMFbot Hardware Detector
 *
 * Detects GPU/CPU capabilities to determine:
 * - Which AI models can run locally
 * - Whether to use cloud API fallback
 * - Optimal inference settings
 *
 * @license Apache-2.0
 */

import si from "systeminformation";

export interface GPUInfo {
    vendor: string;
    model: string;
    vram: number; // in MB
    driver?: string;
    cudaVersion?: string;
    type: "nvidia" | "amd" | "intel" | "apple" | "unknown";
}

export interface CPUInfo {
    manufacturer: string;
    brand: string;
    cores: number;
    physicalCores: number;
    speed: number; // in GHz
    hasAvx: boolean;
    hasAvx2: boolean;
}

export interface MemoryInfo {
    total: number; // in bytes
    available: number;
    used: number;
}

export interface AppleSiliconInfo {
    isAppleSilicon: boolean;
    chipGeneration: "M1" | "M2" | "M3" | "M4" | "unknown";
    hasNeuralEngine: boolean;
    unifiedMemoryGB: number;
    supportsMetalAcceleration: boolean;
}

export interface ModelRecommendation {
    llmModel: string;
    llmQuantization: "full" | "q8" | "q4";
    imageModel: string;
    videoModel: string;
    useQuantizedModels: boolean;
    enableMetalAcceleration: boolean;
    enableMPS: boolean;
    fallbackToAPI: boolean;
}

export interface HardwareCapabilities {
    gpus: GPUInfo[];
    cpu: CPUInfo;
    memory: MemoryInfo;
    platform: NodeJS.Platform;
    arch: string;

    // Apple Silicon specific
    appleSilicon: AppleSiliconInfo;

    // Recommendations
    canRunLocalVideo: boolean;
    canRunLocalImage: boolean;
    canRunLLM: boolean;
    recommendedVideoBackend: "local" | "api";
    recommendedImageBackend: "local" | "api";
    modelRecommendation: ModelRecommendation;
    warnings: string[];
}

// Minimum requirements for different tasks
const REQUIREMENTS = {
    VIDEO_GENERATION: {
        minVRAM: 8000, // 8GB for LTX-Video distilled
        minRAM: 16 * 1024 * 1024 * 1024, // 16GB
        recommendedVRAM: 16000, // 16GB for full quality
        quantizedMinRAM: 8 * 1024 * 1024 * 1024, // 8GB for quantized
    },
    IMAGE_GENERATION: {
        minVRAM: 6000, // 6GB for Flux
        minRAM: 8 * 1024 * 1024 * 1024, // 8GB
        recommendedVRAM: 12000, // 12GB for best quality
        quantizedMinRAM: 4 * 1024 * 1024 * 1024, // 4GB for quantized
    },
    LLM: {
        minRAM: 8 * 1024 * 1024 * 1024, // 8GB for small models
        recommendedRAM: 16 * 1024 * 1024 * 1024, // 16GB for larger models
        quantizedMinRAM: 4 * 1024 * 1024 * 1024, // 4GB for Q4 models
    },
};

export class HardwareDetector {
    /**
     * Detect all hardware capabilities
     */
    async detect(): Promise<HardwareCapabilities> {
        const [gpus, cpu, memory] = await Promise.all([
            this.detectGPUs(),
            this.detectCPU(),
            this.detectMemory(),
        ]);

        // Detect Apple Silicon
        const appleSilicon = await this.detectAppleSilicon(cpu, memory);

        const capabilities: HardwareCapabilities = {
            gpus,
            cpu,
            memory,
            platform: process.platform,
            arch: process.arch,
            appleSilicon,
            canRunLocalVideo: false,
            canRunLocalImage: false,
            canRunLLM: false,
            recommendedVideoBackend: "api",
            recommendedImageBackend: "api",
            modelRecommendation: this.getDefaultModelRecommendation(),
            warnings: [],
        };

        // Analyze capabilities and set recommendations
        this.analyzeCapabilities(capabilities);

        return capabilities;
    }

    /**
     * Detect Apple Silicon information
     */
    private async detectAppleSilicon(cpu: CPUInfo, memory: MemoryInfo): Promise<AppleSiliconInfo> {
        const isAppleSilicon = process.platform === "darwin" && process.arch === "arm64";

        if (!isAppleSilicon) {
            return {
                isAppleSilicon: false,
                chipGeneration: "unknown",
                hasNeuralEngine: false,
                unifiedMemoryGB: 0,
                supportsMetalAcceleration: false,
            };
        }

        // Detect chip generation from CPU brand
        let chipGeneration: "M1" | "M2" | "M3" | "M4" | "unknown" = "unknown";
        const cpuBrand = cpu.brand.toLowerCase();

        if (cpuBrand.includes("m4")) chipGeneration = "M4";
        else if (cpuBrand.includes("m3")) chipGeneration = "M3";
        else if (cpuBrand.includes("m2")) chipGeneration = "M2";
        else if (cpuBrand.includes("m1")) chipGeneration = "M1";

        return {
            isAppleSilicon: true,
            chipGeneration,
            hasNeuralEngine: true, // All Apple Silicon has Neural Engine
            unifiedMemoryGB: memory.total / (1024 * 1024 * 1024),
            supportsMetalAcceleration: true, // All Apple Silicon supports Metal
        };
    }

    /**
     * Get default model recommendation
     */
    private getDefaultModelRecommendation(): ModelRecommendation {
        return {
            llmModel: "llama3.2",
            llmQuantization: "full",
            imageModel: "flux-schnell",
            videoModel: "ltx-video-distilled",
            useQuantizedModels: false,
            enableMetalAcceleration: false,
            enableMPS: false,
            fallbackToAPI: true,
        };
    }

    /**
     * Detect available GPUs
     */
    private async detectGPUs(): Promise<GPUInfo[]> {
        try {
            const graphics = await si.graphics();
            const gpus: GPUInfo[] = [];

            for (const controller of graphics.controllers) {
                const gpu: GPUInfo = {
                    vendor: controller.vendor || "Unknown",
                    model: controller.model || "Unknown",
                    vram: controller.vram || 0,
                    driver: controller.driverVersion,
                    type: this.classifyGPU(controller.vendor || ""),
                };

                // Detect CUDA version for NVIDIA GPUs
                if (gpu.type === "nvidia") {
                    gpu.cudaVersion = await this.detectCudaVersion();
                }

                gpus.push(gpu);
            }

            return gpus;
        } catch (error) {
            console.error("Error detecting GPUs:", error);
            return [];
        }
    }

    /**
     * Classify GPU vendor type
     */
    private classifyGPU(
        vendor: string
    ): "nvidia" | "amd" | "intel" | "apple" | "unknown" {
        const v = vendor.toLowerCase();
        if (v.includes("nvidia")) return "nvidia";
        if (v.includes("amd") || v.includes("radeon")) return "amd";
        if (v.includes("intel")) return "intel";
        if (v.includes("apple")) return "apple";
        return "unknown";
    }

    /**
     * Detect CUDA version
     */
    private async detectCudaVersion(): Promise<string | undefined> {
        try {
            const { execa } = await import("execa");
            const result = await execa("nvcc", ["--version"], { reject: false });

            if (result.exitCode === 0) {
                const match = result.stdout.match(/release (\d+\.\d+)/);
                return match ? match[1] : undefined;
            }
        } catch {
            // CUDA not available
        }
        return undefined;
    }

    /**
     * Detect CPU information
     */
    private async detectCPU(): Promise<CPUInfo> {
        try {
            const cpu = await si.cpu();

            return {
                manufacturer: cpu.manufacturer,
                brand: cpu.brand,
                cores: cpu.cores,
                physicalCores: cpu.physicalCores,
                speed: cpu.speed,
                hasAvx: cpu.flags?.includes("avx") || false,
                hasAvx2: cpu.flags?.includes("avx2") || false,
            };
        } catch (error) {
            console.error("Error detecting CPU:", error);
            return {
                manufacturer: "Unknown",
                brand: "Unknown",
                cores: 1,
                physicalCores: 1,
                speed: 0,
                hasAvx: false,
                hasAvx2: false,
            };
        }
    }

    /**
     * Detect memory information
     */
    private async detectMemory(): Promise<MemoryInfo> {
        try {
            const mem = await si.mem();

            return {
                total: mem.total,
                available: mem.available,
                used: mem.used,
            };
        } catch (error) {
            console.error("Error detecting memory:", error);
            return {
                total: 0,
                available: 0,
                used: 0,
            };
        }
    }

    /**
     * Analyze capabilities and set recommendations
     */
    private analyzeCapabilities(caps: HardwareCapabilities): void {
        // Find best GPU
        const bestGPU = caps.gpus.reduce<GPUInfo | null>((best, gpu) => {
            if (!best || gpu.vram > best.vram) return gpu;
            return best;
        }, null);

        const maxVRAM = bestGPU?.vram || 0;
        const hasNvidia = caps.gpus.some((g) => g.type === "nvidia");
        const hasAppleSilicon =
            caps.platform === "darwin" && caps.arch === "arm64";

        // Check LLM capability
        caps.canRunLLM = caps.memory.total >= REQUIREMENTS.LLM.minRAM;
        if (!caps.canRunLLM) {
            caps.warnings.push(
                `Insufficient RAM for local LLM. Recommended: ${REQUIREMENTS.LLM.minRAM / (1024 * 1024 * 1024)}GB`
            );
        }

        // Check video generation capability
        if (hasNvidia && maxVRAM >= REQUIREMENTS.VIDEO_GENERATION.minVRAM) {
            caps.canRunLocalVideo = true;
            caps.recommendedVideoBackend = "local";
        } else if (
            hasAppleSilicon &&
            caps.memory.total >= REQUIREMENTS.VIDEO_GENERATION.minRAM
        ) {
            // Apple Silicon can use MPS with unified memory
            caps.canRunLocalVideo = true;
            caps.recommendedVideoBackend = "local";
            caps.warnings.push(
                "Apple Silicon detected. Video generation will use MPS backend."
            );
        } else {
            caps.canRunLocalVideo = false;
            caps.recommendedVideoBackend = "api";
            caps.warnings.push(
                `Insufficient GPU for local video generation (need ${REQUIREMENTS.VIDEO_GENERATION.minVRAM}MB VRAM). Using API fallback.`
            );
        }

        // Check image generation capability
        if (hasNvidia && maxVRAM >= REQUIREMENTS.IMAGE_GENERATION.minVRAM) {
            caps.canRunLocalImage = true;
            caps.recommendedImageBackend = "local";
        } else if (
            hasAppleSilicon &&
            caps.memory.total >= REQUIREMENTS.IMAGE_GENERATION.minRAM
        ) {
            caps.canRunLocalImage = true;
            caps.recommendedImageBackend = "local";
        } else if (maxVRAM >= REQUIREMENTS.IMAGE_GENERATION.minVRAM) {
            // Other GPUs might work with reduced performance
            caps.canRunLocalImage = true;
            caps.recommendedImageBackend = "local";
            caps.warnings.push(
                "Non-NVIDIA GPU detected. Image generation may have reduced performance."
            );
        } else {
            caps.canRunLocalImage = false;
            caps.recommendedImageBackend = "api";
            caps.warnings.push(
                `Insufficient GPU for local image generation (need ${REQUIREMENTS.IMAGE_GENERATION.minVRAM}MB VRAM). Using API fallback.`
            );
        }

        // Additional warnings
        if (maxVRAM < REQUIREMENTS.VIDEO_GENERATION.recommendedVRAM && caps.canRunLocalVideo) {
            caps.warnings.push(
                `Video generation possible but may be slow. Recommended: ${REQUIREMENTS.VIDEO_GENERATION.recommendedVRAM}MB VRAM.`
            );
        }

        if (!caps.cpu.hasAvx2) {
            caps.warnings.push(
                "CPU lacks AVX2 support. Some ML operations may be slower."
            );
        }
    }

    /**
     * Get a human-readable summary
     */
    static formatSummary(caps: HardwareCapabilities): string {
        const lines: string[] = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║                    AMFbot Hardware Report                     ║",
            "╠══════════════════════════════════════════════════════════════╣",
            `║  Platform: ${(caps.platform + " " + caps.arch).padEnd(49)}║`,
            `║  CPU: ${caps.cpu.brand.substring(0, 54).padEnd(54)}║`,
            `║  Cores: ${caps.cpu.cores} (${caps.cpu.physicalCores} physical)`.padEnd(
                65
            ) + "║",
            `║  RAM: ${(caps.memory.total / (1024 * 1024 * 1024)).toFixed(1)}GB total, ${(caps.memory.available / (1024 * 1024 * 1024)).toFixed(1)}GB available`.padEnd(
                63
            ) + "║",
            "╠══════════════════════════════════════════════════════════════╣",
        ];

        if (caps.gpus.length > 0) {
            lines.push("║  GPUs:".padEnd(65) + "║");
            for (const gpu of caps.gpus) {
                lines.push(
                    `║    • ${gpu.model.substring(0, 40)} (${gpu.vram}MB VRAM)`.padEnd(
                        64
                    ) + "║"
                );
            }
        } else {
            lines.push("║  GPUs: None detected".padEnd(65) + "║");
        }

        lines.push(
            "╠══════════════════════════════════════════════════════════════╣"
        );
        lines.push("║  Capabilities:".padEnd(65) + "║");
        lines.push(
            `║    • Local LLM: ${caps.canRunLLM ? "✓ Supported" : "✗ API only"}`.padEnd(
                64
            ) + "║"
        );
        lines.push(
            `║    • Local Image Gen: ${caps.canRunLocalImage ? "✓ Supported" : "✗ API only"}`.padEnd(
                64
            ) + "║"
        );
        lines.push(
            `║    • Local Video Gen: ${caps.canRunLocalVideo ? "✓ Supported" : "✗ API only"}`.padEnd(
                64
            ) + "║"
        );

        if (caps.warnings.length > 0) {
            lines.push(
                "╠══════════════════════════════════════════════════════════════╣"
            );
            lines.push("║  ⚠ Warnings:".padEnd(65) + "║");
            for (const warning of caps.warnings) {
                const wrapped = warning.match(/.{1,56}/g) || [warning];
                for (const line of wrapped) {
                    lines.push(`║    ${line}`.padEnd(64) + "║");
                }
            }
        }

        lines.push(
            "╚══════════════════════════════════════════════════════════════╝"
        );

        return lines.join("\n");
    }
}

export default HardwareDetector;
