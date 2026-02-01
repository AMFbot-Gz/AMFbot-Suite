'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Mic, Paperclip, Terminal, cpu, Activity, Zap, Box, Settings, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type Message = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
};

export default function Home() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'System initialized. Gateway active. How may I assist you today?',
      timestamp: new Date(),
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const [sessionId, setSessionId] = useState<string>('');

  useEffect(() => {
    // Restore session ID if needed, or keeping it in state is fine for SPA
    // For now we start fresh on refresh or could load from local storage
    const stored = localStorage.getItem('amfbot_session_id');
    if (stored) setSessionId(stored);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    const tempAiMsgId = (Date.now() + 1).toString();
    const aiMsgPlaceholder: Message = {
      id: tempAiMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, aiMsgPlaceholder]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:3001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content, sessionId }),
      });

      if (!response.body) throw new Error('No response body');

      // Check for session ID header
      const newSessionId = response.headers.get('X-Session-Id');
      if (newSessionId && newSessionId !== sessionId) {
        setSessionId(newSessionId);
        localStorage.setItem('amfbot_session_id', newSessionId);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        aiContent += chunk;

        setMessages((prev) =>
          prev.map(m => m.id === tempAiMsgId ? { ...m, content: aiContent } : m)
        );
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) =>
        prev.map(m => m.id === tempAiMsgId ? { ...m, content: "Error: Could not connect to AMFbot Gateway." } : m)
      );
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border/40 bg-card/50 backdrop-blur-xl hidden md:flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center glow">
            <Zap className="w-5 h-5 text-secondary-foreground fill-current" />
          </div>
          <h1 className="text-xl font-bold tracking-tighter">AMFbot<span className="text-secondary">.Suite</span></h1>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          <SidebarItem icon={<Terminal className="w-4 h-4" />} label="Terminal" active />
          <SidebarItem icon={<Activity className="w-4 h-4" />} label="Activity" />
          <SidebarItem icon={<Box className="w-4 h-4" />} label="MCP Servers" />
          <SidebarItem icon={<Settings className="w-4 h-4" />} label="Settings" />
        </nav>

        <div className="p-4 border-t border-border/40">
          <div className="bg-muted/50 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              <span>System Status</span>
              <span className="text-green-500">● Online</span>
            </div>
            <div className="space-y-1">
              <StatusRow label="CPU" value="12%" icon={<Cpu className="w-3 h-3" />} />
              <StatusRow label="RAM" value="4.2GB" icon={<Box className="w-3 h-3" />} />
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative bg-gradient-to-b from-background to-background/95">
        {/* Header (Mobile only mostly, or global status) */}
        <header className="h-16 border-b border-border/40 flex items-center justify-between px-6 bg-background/50 backdrop-blur-md z-10">
          <div className="md:hidden font-bold">AMFbot</div>
          <div className="flex items-center gap-4 ml-auto">
            <div className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">
              GATEWAY: <span className="text-secondary">CONNECTED</span> // OLLAMA: <span className="text-green-400">READY</span>
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex w-full",
                  msg.role === 'user' ? "justify-end" : "justify-start"
                )}
              >
                <div className={cn(
                  "max-w-[80%] md:max-w-[60%] rounded-2xl px-5 py-3 shadow-sm",
                  msg.role === 'user'
                    ? "bg-primary text-primary-foreground rounded-br-none"
                    : "bg-muted rounded-bl-none border border-border/50"
                )}>
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-[10px] opacity-50 mt-2 uppercase tracking-wide">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </motion.div>
            ))}
            {isTyping && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                <div className="bg-muted rounded-2xl rounded-bl-none px-4 py-2 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 pb-8 bg-gradient-to-t from-background via-background to-transparent z-20">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-secondary/50 to-primary/50 rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-500"></div>
            <form onSubmit={handleSubmit} className="relative bg-card rounded-xl border border-border shadow-2xl flex items-center p-2 pr-4 overflow-hidden">
              <button type="button" className="p-3 text-muted-foreground hover:text-foreground transition-colors">
                <Paperclip className="w-5 h-5" />
              </button>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Command the system..."
                className="flex-1 bg-transparent border-none outline-none text-foreground placeholder-muted-foreground px-2 py-3"
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button type="button" className="p-2 text-muted-foreground hover:text-foreground transition-colors rounded-full hover:bg-muted/50">
                  <Mic className="w-5 h-5" />
                </button>
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="p-2 bg-secondary text-secondary-foreground rounded-lg hover:opacity-90 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(34,211,238,0.3)]"
                >
                  <Send className="w-5 h-5 ml-0.5" />
                </button>
              </div>
            </form>
          </div>
          <p className="text-center text-xs text-muted-foreground mt-3">
            AMFbot Suite v1.0 • Local System Access Authorized
          </p>
        </div>
      </main>
    </div>
  );
}

function SidebarItem({ icon, label, active = false }: { icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <button className={cn(
      "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
      active
        ? "bg-secondary/10 text-secondary hover:bg-secondary/20"
        : "text-muted-foreground hover:bg-muted hover:text-foreground"
    )}>
      {icon}
      <span>{label}</span>
      {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-secondary shadow-[0_0_8px_theme('colors.secondary.DEFAULT')]" />}
    </button>
  )
}

function StatusRow({ label, value, icon }: { label: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <span className="font-mono">{value}</span>
    </div>
  )
}
