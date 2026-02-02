import { glob } from "glob";
import fs from "fs-extra";
import yaml from "js-yaml";
import path from "path";

export interface SkillMetadata {
    name: string;
    description: string;
    domain: string;
    tools: string[];
    version: string;
    content: string;
}

/**
 * AMF-OS Skill Manager
 * Dynamically loads and parses the Elite Skill Pack.
 */
export class SkillManager {
    private skills: Map<string, SkillMetadata> = new Map();

    async loadAll(skillsDir: string = "./skills") {
        const files = await glob("**/*.md", { cwd: skillsDir });

        for (const file of files) {
            if (file === "SKILL_TEMPLATE.md") continue;

            const fullPath = path.join(skillsDir, file);
            const rawContent = await fs.readFile(fullPath, "utf-8");

            // Parse YAML frontmatter
            const match = rawContent.match(/^---\n([\s\S]*?)\n---/);
            if (match) {
                try {
                    const metadata = yaml.load(match[1]) as any;
                    const content = rawContent.replace(match[0], "").trim();

                    this.skills.set(metadata.name, {
                        ...metadata,
                        content
                    });
                } catch (e) {
                    console.error(`❌ SkillManager: Failed to parse \${file}:`, e);
                }
            }
        }
        console.log(`🌀 SkillManager: \${this.skills.size} skills synchronized.`);
    }

    getSkillsByDomain(domain: string): SkillMetadata[] {
        return Array.from(this.skills.values()).filter(s => s.domain === domain);
    }

    getAllSkills(): SkillMetadata[] {
        return Array.from(this.skills.values());
    }
}
