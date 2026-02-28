'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Send, Mic, Paperclip, Terminal, Activity, Zap, Box,
  Settings, Cpu, LayoutDashboard, MessageSquare, Shield,
  ChevronRight, Search, Plus, Trash2, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type Message = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
};

type Session = {
  id: string;
  name: string;
  lastActiveAt: Date;
};

type AgentStatus = {
  name: string;
  model: string;
  status: 'idle' | 'busy' | 'offline';
  load: number;
};

export default function Home() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeTab, setActiveTab] = useState<'chat' | 'agents' | 'activity'>('chat');
  const [systemStats, setSystemStats] = useState({ cpu: '0%', ram: '0GB' });
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { name: 'Primary Agent', model: 'llama3.2', status: 'idle', load: 0 },
    { name: 'Media Specialist', model: 'flux-schnell', status: 'offline', load: 0 },
    { name: 'Security Auditor', model: 'mistral', status: 'idle', load: 0 },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /* eslint-disable react-hooks/exhaustive-deps */
  const fetchSessions = async () => {
    try {
      const res = await fetch('http://localhost:3001/api/sessions');
      if (res.ok) {
        const data = await res.json();
        const serverSessions = data.sessions.map((s: any) => ({
          id: s.id,
          // Use metadata name or fallback
          name: s.metadata?.name || `Session ${s.id.slice(0, 8)}`,
          lastActiveAt: new Date(s.lastActiveAt)
        }));
        setSessions(serverSessions);
      }
    } catch (e) {
      console.error("Failed to fetch sessions", e);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const stored = localStorage.getItem('amfbot_session_id');
    if (stored) {
      setSessionId(stored);
      // In a real app, we fetch history here
      setMessages([
        { id: '1', role: 'assistant', content: 'Session restored. How can I help?', timestamp: new Date() }
      ]);
    } else {
      createNewSession();
    }

    fetchSessions(); // Initial fetch

    // Periodically update stats and sessions
    const interval = setInterval(() => {
      setSystemStats({
        cpu: `${Math.floor(Math.random() * 20 + 5)}%`,
        ram: `${(Math.random() * 2 + 4).toFixed(1)}GB`
      });
      fetchSessions(); // Auto-refresh sessions
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const createNewSession = () => {
    const newId = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString();
    setSessionId(newId);
    localStorage.setItem('amfbot_session_id', newId);
    setMessages([{ id: 'init', role: 'assistant', content: 'New session started. System ready.', timestamp: new Date() }]);
    // Session creation happens on first message or we could trigger it via API
    // For now client-side ID generation is fine if passed to server
    // We update local list optimistically
    setSessions(prev => [{ id: newId, name: `New Session`, lastActiveAt: new Date() }, ...prev]);
  };

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
    <div className="flex h-screen overflow-hidden bg-[#050505] text-white font-sans selection:bg-cyan-500/30">
      {/* Sidebar */}
      <aside className="w-72 border-r border-white/5 bg-[#0a0a0a] hidden md:flex flex-col z-30">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.5)]">
              <Zap className="w-6 h-6 text-white fill-current" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tighter leading-none">AMFBOT</h1>
              <span className="text-[10px] text-cyan-500 font-mono tracking-widest uppercase">Sovereign OS</span>
            </div>
          </div>

          <nav className="space-y-1 mb-8">
            <NavItem icon={<LayoutDashboard className="w-4 h-4" />} label="Dashboard" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} />
            <NavItem icon={<Activity className="w-4 h-4" />} label="Agents" active={activeTab === 'agents'} onClick={() => setActiveTab('agents')} />
            <NavItem icon={<Box className="w-4 h-4" />} label="MCP Hub" />
            <NavItem icon={<Shield className="w-4 h-4" />} label="Security" />
          </nav>

          <div className="mt-auto">
            <div className="flex items-center justify-between mb-2 px-2">
              <span className="text-[10px] uppercase tracking-wider text-white/40 font-bold">Sessions</span>
              <button onClick={createNewSession} className="p-1 hover:bg-white/5 rounded">
                <Plus className="w-3 h-3 text-white/60" />
              </button>
            </div>
            <div className="space-y-1 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
              {sessions.length === 0 ? (
                <div className="text-[10px] text-white/20 p-2 text-center">No recent sessions</div>
              ) : (
                sessions.map(s => (
                  <button
                    key={s.id}
                    onClick={() => setSessionId(s.id)}
                    className={cn(
                      "w-full text-left px-3 py-2 rounded-lg text-xs transition-colors group flex items-center gap-2",
                      sessionId === s.id ? "bg-white/10 text-white" : "text-white/40 hover:bg-white/5 hover:text-white/60"
                    )}>
                    <MessageSquare className="w-3 h-3 shrink-0" />
                    <span className="truncate flex-1">{s.name}</span>
                    <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="p-4 bg-white/[0.02] border-t border-white/5">
          <div className="flex items-center justify-between text-[10px] text-white/20 mb-3 uppercase tracking-tighter font-bold">
            <span>Core Telemetry</span>
            <span className="text-green-500 flex items-center gap-1">
              <span className="w-1 h-1 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-white/5 p-2 rounded-lg">
              <div className="text-[8px] text-white/40 mb-1">CPU LOAD</div>
              <div className="text-xs font-mono text-cyan-400">{systemStats.cpu}</div>
            </div>
            <div className="bg-white/5 p-2 rounded-lg">
              <div className="text-[8px] text-white/40 mb-1">VRAM USE</div>
              <div className="text-xs font-mono text-blue-400">{systemStats.ram}</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative">
        {/* Navbar */}
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 bg-[#050505]/80 backdrop-blur-xl z-20">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 text-sm font-medium text-white/80">
              <Terminal className="w-4 h-4 text-cyan-500" />
              <span>Gateway 1.0.0</span>
            </div>
            <div className="h-4 w-px bg-white/10" />
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-[10px] font-mono text-white/40">NODE_LOCAL_READY</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-white/5 rounded-full transition-colors relative">
              <RefreshCw className="w-4 h-4 text-white/60" />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-blue-500 rounded-full" />
            </button>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-white/10 flex items-center justify-center">
              <Settings className="w-4 h-4 text-white/60" />
            </div>
          </div>
        </header>

        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Chat Display */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto opacity-100">
                  <div className="w-16 h-16 rounded-3xl bg-white/5 flex items-center justify-center mb-6">
                    <Zap className="w-8 h-8 text-cyan-500" />
                  </div>
                  <h2 className="text-xl font-bold mb-2 text-white/90">Welcome to AMFbot Suite</h2>
                  <p className="text-sm text-white/40 leading-relaxed">
                    Your local system control plane is active. Command the machine using natural language.
                  </p>
                </div>
              )}
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, scale: 0.98, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className={cn(
                      "flex w-full group",
                      msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                  >
                    <div className={cn(
                      "max-w-[85%] md:max-w-[70%] rounded-2xl px-6 py-4 transition-all duration-300 relative",
                      msg.role === 'user'
                        ? "bg-gradient-to-br from-blue-600 to-cyan-600 text-white shadow-[0_10px_30px_rgba(6,182,212,0.2)] rounded-br-none"
                        : "bg-white/[0.03] border border-white/5 text-white/90 rounded-bl-none hover:bg-white/[0.05]"
                    )}>
                      {msg.role === 'assistant' && (
                        <div className="absolute -left-12 top-0 text-cyan-500/40 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Zap className="w-6 h-6" />
                        </div>
                      )}
                      <p className="leading-relaxed whitespace-pre-wrap text-sm md:text-base selection:bg-white/20">
                        {msg.content}
                      </p>
                      <div className="flex items-center gap-2 mt-4 opacity-30 group-hover:opacity-60 transition-opacity">
                        <span className="text-[10px] font-mono tracking-widest uppercase">
                          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {msg.role === 'assistant' && <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-1.5 rounded">AI_RESPONSE</span>}
                      </div>
                    </div>
                  </motion.div>
                ))}
                {isTyping && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                    <div className="bg-white/[0.03] border border-white/10 rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-cyan-500/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 bg-cyan-500/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 bg-cyan-500/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} />
            </div>

            {/* Input Section */}
            <div className="p-8">
              <div className="max-w-4xl mx-auto">
                <form onSubmit={handleSubmit} className="relative group">
                  {/* Input Glow */}
                  <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-purple-500/20 rounded-2xl blur-xl opacity-0 group-focus-within:opacity-100 transition duration-1000"></div>

                  <div className="relative bg-[#0d0d0d] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                    <div className="flex items-center p-1 border-b border-white/5 bg-white/[0.01]">
                      <button type="button" className="p-2 text-white/30 hover:text-white/60 transition-colors">
                        <Terminal className="w-4 h-4" />
                      </button>
                      <div className="text-[9px] uppercase tracking-widest text-white/20 font-bold ml-1">Local Session: {sessionId}</div>
                    </div>
                    <div className="flex items-center p-2">
                      <button type="button" className="p-3 text-white/40 hover:text-white transition-colors">
                        <Paperclip className="w-5 h-5" />
                      </button>
                      <textarea
                        rows={1}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit(e);
                          }
                        }}
                        placeholder="Command the Sovereign AI..."
                        className="flex-1 bg-transparent border-none outline-none text-white placeholder-white/20 px-4 py-3 resize-none max-h-32 text-base"
                        autoFocus
                      />
                      <div className="flex items-center gap-2 px-2">
                        <button type="button" className="p-3 text-white/40 hover:text-cyan-500 transition-colors active:scale-95">
                          <Mic className="w-5 h-5" />
                        </button>
                        <button
                          type="submit"
                          disabled={!input.trim() || isTyping}
                          className="w-10 h-10 bg-cyan-500 text-black rounded-xl flex items-center justify-center hover:bg-cyan-400 transition-all disabled:opacity-30 disabled:grayscale shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-95"
                        >
                          <Send className="w-5 h-5 translate-x-0.5 -translate-y-px" />
                        </button>
                      </div>
                    </div>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="flex-1 overflow-y-auto p-12 custom-scrollbar">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h2 className="text-3xl font-bold text-white/90">Neural Nodes</h2>
                  <p className="text-white/40 text-sm mt-1">Monitor and configure specialized AI agents.</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-white/30 uppercase font-mono tracking-tighter">Total Active: 3</span>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                {agentStatuses.map((agent, i) => (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="bg-white/[0.03] border border-white/5 rounded-2xl p-6 hover:bg-white/[0.05] transition-colors relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        agent.status === 'idle' ? "bg-green-500" : agent.status === 'busy' ? "bg-yellow-500" : "bg-red-500"
                      )} />
                    </div>
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Cpu className="w-6 h-6 text-cyan-400" />
                      </div>
                      <div>
                        <h3 className="font-bold text-lg text-white/90">{agent.name}</h3>
                        <div className="text-[10px] font-mono text-white/30 uppercase">{agent.model}</div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] text-white/40 font-bold">
                          <span>COMPUTE LOAD</span>
                          <span>{agent.load}%</span>
                        </div>
                        <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-cyan-500/50 rounded-full"
                            style={{ width: `${agent.load}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-white/20 uppercase font-bold tracking-widest">Status</span>
                          <span className="text-[10px] text-white/60 font-mono text-xs capitalize">{agent.status}</span>
                        </div>
                        <button className="text-[10px] text-white/40 hover:text-white uppercase font-bold tracking-widest transition-colors flex items-center gap-1 group/btn">
                          Configure <ChevronRight className="w-3 h-3 group-hover/btn:translate-x-1 transition-transform" />
                        </button>
                      </div>
                    </div>

                    <div className="absolute -bottom-6 -right-6 w-24 h-24 bg-cyan-500/5 blur-[40px] rounded-full" />
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.1);
        }
      `}</style>
    </div>
  );
}

function NavItem({ icon, label, active = false, onClick }: { icon: React.ReactNode, label: string, active?: boolean, onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 relative group",
        active
          ? "bg-white/[0.05] text-cyan-400 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]"
          : "text-white/40 hover:bg-white/[0.02] hover:text-white/70"
      )}>
      {active && <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-cyan-500 rounded-full shadow-[0_0_10px_rgba(6,182,212,0.8)]" />}
      <div className={cn("transition-transform group-hover:scale-110", active ? "text-cyan-400" : "text-white/40")}>
        {icon}
      </div>
      <span>{label}</span>
    </button>
  )
}
