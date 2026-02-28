import { setGlobalDispatcher, ProxyAgent } from "undici";
import chalk from "chalk";

/**
 * Initialize the system-wide network dispatcher.
 * This allows for proxying and network isolation as requested.
 */
export function initializeNetwork() {
    const proxyUrl = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;

    if (proxyUrl) {
        console.log(chalk.blue(`🌐 Network: Using proxy dispatcher via ${proxyUrl}`));
        const dispatcher = new ProxyAgent(proxyUrl);
        setGlobalDispatcher(dispatcher);
    } else {
        console.log(chalk.dim("🌐 Network: Using direct connection (no proxy configured)"));
    }
}
