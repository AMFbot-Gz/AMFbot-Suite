import path from "path";
import { env } from "../config/env.js";

/**
 * Sovereign Path Validator v2.6
 * Cross-platform LFI Protection (macOS, Linux, Windows).
 */
export class PathValidator {
    private static readonly WORKSPACE_ROOT = path.normalize(path.resolve(env.WORKSPACE_ROOT || process.cwd()));
    private static readonly ALLOWED_DIRS = [
        path.normalize(path.resolve(process.env.HOME || process.env.USERPROFILE || "", ".amfbot")),
        path.normalize(path.resolve(process.platform === "win32" ? "C:/temp/amfbot" : "/tmp/amfbot"))
    ];

    /**
     * Validates if a path is safe to access.
     * Prevents directory traversal (../../) and restricts access to approved zones.
     */
    static validate(targetPath: string): { safe: boolean; resolvedPath: string; error?: string } {
        try {
            // Support ~ expansion
            let processedPath = targetPath;
            if (targetPath.startsWith("~")) {
                const home = process.env.HOME || process.env.USERPROFILE || "";
                processedPath = path.join(home, targetPath.slice(1));
            }

            const absolutePath = path.normalize(path.resolve(processedPath));

            // Case-insensitive comparison for Windows
            const isWindows = process.platform === "win32";
            const compare = (a: string, b: string) => isWindows ? a.toLowerCase() : a;

            // 1. Check if it's within WORKSPACE_ROOT
            if (compare(absolutePath).startsWith(compare(this.WORKSPACE_ROOT))) {
                return { safe: true, resolvedPath: absolutePath };
            }

            // 2. Check if it's within ALLOWED_DIRS
            const isAllowed = this.ALLOWED_DIRS.some(dir => compare(absolutePath).startsWith(compare(dir)));
            if (isAllowed) {
                return { safe: true, resolvedPath: absolutePath };
            }

            return {
                safe: false,
                resolvedPath: absolutePath,
                error: `Access Denied: Path [\${absolutePath}] outside of authorized boundaries (LFI Protection).`
            };
        } catch (e) {
            return { safe: false, resolvedPath: targetPath, error: "Invalid path format." };
        }
    }
}
