import { serve } from '@hono/node-server';
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { streamText } from 'hono/streaming';
import { Agent } from '../core/agent.js';
import { HardwareDetector } from '../core/hardware-detector.js';

const app = new Hono();

// Enable CORS for the frontend
app.use('/*', cors({
  origin: 'http://localhost:3000', // Next.js default port
  allowMethods: ['POST', 'GET', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'X-Session-Id'], // Added X-Session-Id
}));

// Initialize Agent
// In a real scenario, we might want to lazy load or manage sessions
const agent = new Agent({
  model: 'llama3.2', // dynamic config TODO
  ollamaHost: process.env.OLLAMA_HOST || 'http://localhost:11434',
});

// Status Endpoint
app.get('/api/status', async (c) => {
  const detector = new HardwareDetector();
  const hw = await detector.detect();
  // Quick health check on Ollama via agent if needed, or separate
  return c.json({
    status: 'online',
    version: '1.0.0',
    hardware: hw,
  });
});

// Chat Endpoint
app.post('/api/chat', async (c) => {
  const body = await c.req.json();
  const { message, sessionId } = body;
  // Create session if needed
  let currentSessionId = sessionId;
  if (!currentSessionId) {
    const session = agent.createSession();
    currentSessionId = session.id;
  }

  // Ensure session exists (in case client sent a bad ID)
  // agent.chat handles retrieval, but we might want to check
  const session = await agent.getSession(currentSessionId);
  if (!session) {
    // If provided session not found, create new
    const newSession = agent.createSession();
    currentSessionId = newSession.id;
  }

  // Set session ID in header so client can store it
  c.header('X-Session-Id', currentSessionId);

  // Use streamText for Server-Sent Events (SSE) compatible stream
  return streamText(c, async (stream) => {
    // Send session ID as first chunk (meta-data)
    // We'll use a specific prefix to denote system messages if we want,
    // but for now let's just assume the client knows the session ID if they sent it,
    // OR we can send a custom header. Hono streamText might commit headers early.
    // Let's rely on the client handling the response.

    // Actually, simple text stream is fine. Frontend will append.
    // But we should header the session ID if we created it.
    // Hono stream doesn't easily let us set headers after start, but we can before.
    // However, streamText returns a Response object.

    try {
      const responseStream = await agent.chat(currentSessionId, message);
      for await (const chunk of responseStream) {
        await stream.write(chunk);
      }
    } catch (e) {
      console.error('Chat error:', e);
      await stream.write(`\nError: ${e}`);
    }
  });
});

// List Sessions Endpoint
app.get('/api/sessions', async (c) => {
  try {
    const sessions = await agent.listSessions();
    return c.json({ sessions });
  } catch (e) {
    console.error('Failed to list sessions', e);
    return c.json({ sessions: [] });
  }
});

console.log('Server is running on port 3001');

serve({
  fetch: app.fetch,
  port: 3001
});
