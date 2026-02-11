import React, { useEffect, useState, useRef } from 'react';
import { Send, Terminal as TerminalIcon, MessageSquare } from 'lucide-react';
import { api, socket } from '../services/api';
import clsx from 'clsx';

// --- Chat Sub-Component ---
const ChatView = ({ messages, input, setInput, sendMessage }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-surface dark:bg-[#1e1e1e] overflow-hidden relative border-r border-border dark:border-[#363636]">
       {/* Header */}
       <div className="h-12 border-b border-border dark:border-[#363636] flex items-center px-4 justify-between bg-surface dark:bg-[#252526]">
          <div className="flex items-center gap-2 text-sm font-semibold text-text dark:text-[#f5f5f5]">
             <MessageSquare size={16} className="text-primary" />
             <span>Interaction</span>
          </div>
          <div className="text-xs text-text-secondary">
             {messages.length} msgs
          </div>
       </div>

       {/* Messages */}
       <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-bg dark:bg-[#121212]" ref={scrollRef}>
          {messages.map((m, i) => {
             const isMe = m.sender === 'Fern' || m.sender.toLowerCase().includes('you');
             return (
                <div key={i} className={clsx("flex flex-col max-w-[85%]", isMe ? "self-end items-end" : "self-start items-start")}>
                   <div className={clsx(
                      "px-3 py-2 rounded-2xl text-sm break-words",
                      isMe 
                        ? "bg-primary text-white rounded-br-sm" 
                        : "bg-surface border border-border dark:bg-[#262626] dark:border-none dark:text-[#e0e0e0] rounded-bl-sm"
                   )}>
                      {m.text}
                   </div>
                   <span className="text-[10px] text-text-tertiary mt-1 px-1">
                      {isMe ? "You" : m.sender} • {new Date(m.timestamp * 1000).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}
                   </span>
                </div>
             );
          })}
       </div>

       {/* Input */}
       <div className="p-3 bg-surface dark:bg-[#252526] border-t border-border dark:border-[#363636]">
          <form onSubmit={sendMessage} className="flex gap-2">
             <input 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Command..."
                className="flex-1 bg-gray-100 dark:bg-[#333] border-none rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none dark:text-white"
             />
             <button type="submit" className="p-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors">
                <Send size={18} />
             </button>
          </form>
       </div>
    </div>
  );
};

// --- Terminal Sub-Component ---
const TerminalView = ({ logs }) => {
  const [filter, setFilter] = useState('ALL');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [logs, filter]);

  const filteredLogs = logs.filter(l => {
    if (filter === 'ALL') return true;
    if (filter === 'ERROR') return l.text.toLowerCase().includes('error') || l.text.toLowerCase().includes('fail');
    if (filter === 'WARNING') return l.text.toLowerCase().includes('warning');
    if (filter === 'NETWORK') return l.text.includes('>>>') || l.text.toLowerCase().includes('network');
    if (filter === 'PLUGIN') return l.text.includes('[') && l.text.includes(']');
    return true;
  });

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e] overflow-hidden font-mono text-xs">
       <div className="h-12 bg-[#252526] border-b border-[#333] flex items-center px-4 justify-between select-none">
          <div className="flex items-center gap-4 text-gray-300">
             <div className="flex items-center gap-2">
                <TerminalIcon size={14} className="text-blue-400" />
                <span>KERNEL LOG</span>
             </div>
             <select 
                value={filter} 
                onChange={(e) => setFilter(e.target.value)}
                className="bg-[#181818] border border-[#444] rounded px-2 py-0.5 text-[10px] outline-none"
             >
                <option value="ALL">ALL</option>
                <option value="ERROR">ERRORS</option>
                <option value="WARNING">WARNINGS</option>
                <option value="NETWORK">NETWORK</option>
                <option value="PLUGIN">PLUGINS</option>
             </select>
          </div>
          <span className="text-gray-500">{filteredLogs.length} lines</span>
       </div>
       
       <div className="flex-1 overflow-y-auto p-3 space-y-1 bg-[#1e1e1e]" ref={scrollRef}>
          {filteredLogs.map((l, i) => (
             <div key={i} className="break-all text-gray-400 hover:bg-[#2a2d2e] leading-tight py-0.5 px-1 rounded-sm">
                <span className="text-gray-600 mr-2 select-none">[{new Date().toLocaleTimeString()}]</span>
                <span className={clsx(
                   l.text.includes("Error") || l.text.includes("FAIL") ? "text-red-400" :
                   l.text.includes("Warning") ? "text-yellow-400" :
                   l.text.includes(">>>") ? "text-green-400" : "text-gray-300"
                )}>{l.text}</span>
             </div>
          ))}
       </div>
    </div>
  );
};

// --- Main Console Layout ---
export default function Console() {
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [input, setInput] = useState("");
  
  // Data Fetching
  useEffect(() => {
    const fetchData = async () => {
       // 1. Logs
       const logRes = await api.get('/logs');
       if (logRes && logRes.logs) setLogs(logRes.logs.map(l => ({ text: l })));
       
       // 2. Chat History
       const chatRes = await api.get('/chat/history');
       if (chatRes && chatRes.messages) setMessages(chatRes.messages);
    };
    fetchData();

    const unsub = socket.subscribe((data) => {
       if (data.type === 'log') {
          setLogs(prev => [...prev.slice(-199), { text: data.text }]);
       }
       if (data.type === 'chat_message') {
          setMessages(prev => [...prev, { ...data, timestamp: data.timestamp || Date.now()/1000 }]);
       }
    });

    return () => unsub();
  }, []);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Optimistic
    const msg = { sender: "You", text: input, timestamp: Date.now()/1000 };
    setMessages(prev => [...prev, msg]);
    
    const payload = input.startsWith('/') ? { text: input } : { text: `/say ${input}` };
    await api.post('/command', payload);
    setInput("");
  };

  return (
    <div className="card h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] flex flex-col md:flex-row overflow-hidden shadow-xl border-none">
       {/* 1. Chat Pane (50%) */}
       <div className="flex-1 md:flex-[0.5] min-h-[50%] md:min-h-0 border-b md:border-b-0">
          <ChatView messages={messages} input={input} setInput={setInput} sendMessage={sendMessage} />
       </div>
       
       {/* 2. Logs Pane (50%) */}
       <div className="flex-1 md:flex-[0.5] min-h-[50%] md:min-h-0">
          <TerminalView logs={logs} />
       </div>
    </div>
  );
}
