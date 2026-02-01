import fs from 'fs-extra';
import path from 'path';
import { Session } from './agent.js';

export class SessionStore {
    private dataDir: string;

    constructor(dataDir: string = './data/sessions') {
        this.dataDir = dataDir;
        fs.ensureDirSync(this.dataDir);
    }

    async saveSession(session: Session): Promise<void> {
        const filePath = path.join(this.dataDir, `${session.id}.json`);
        await fs.writeJson(filePath, session, { spaces: 2 });
    }

    async getSession(sessionId: string): Promise<Session | undefined> {
        const filePath = path.join(this.dataDir, `${sessionId}.json`);
        if (await fs.pathExists(filePath)) {
            const session = await fs.readJson(filePath);
            // Revive dates
            session.createdAt = new Date(session.createdAt);
            session.lastActiveAt = new Date(session.lastActiveAt);
            return session;
        }
        return undefined;
    }

    async getAllSessions(): Promise<Session[]> {
        const files = await fs.readdir(this.dataDir);
        const sessions: Session[] = [];
        for (const file of files) {
            if (file.endsWith('.json')) {
                const session = await this.getSession(file.replace('.json', ''));
                if (session) sessions.push(session);
            }
        }
        return sessions.sort((a, b) => b.lastActiveAt.getTime() - a.lastActiveAt.getTime());
    }
}
