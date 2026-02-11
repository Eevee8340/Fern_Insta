import React, { useState, useEffect, useRef } from 'react';
import { api, socket } from '../services/api';
import { Send, User, Bot, Sparkles, Terminal, Database, Brain, ChevronRight, Activity } from 'lucide-react';

export default function Playground() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [sender, setSender] = useState("TestUser"); // Default
  const [profiles, setProfiles] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [showDebug, setShowDebug] = useState(true);
  const [debugInfo, setDebugInfo] = useState(null);
  
  const scrollRef = useRef(null);

  // Fetch Profiles
  useEffect(() => {
    api.get('/profiles/lite').then(data => {
      if (data && data.profiles) {
        setProfiles(data.profiles);
        if (data.profiles.length > 0) setSender(data.profiles[0].handle);
      }
    });
  }, []);

  // WebSocket Listeners
  useEffect(() => {
    const unsub = socket.subscribe((data) => {
      // 1. Full Message (Finalize)
      if (data.type === 'playground_message') {
        // If we were streaming, clear the stream buffer as the full message has arrived
        setStreamingContent(""); 
        
        setMessages(prev => [...prev, {
          role: data.role === 'assistant' ? 'assistant' : 'user',
          text: data.text,
          sender: data.sender,
          time: new Date().toLocaleTimeString()
        }]);
      }
      
      // 2. Typing Status
      else if (data.type === 'typing_status') {
        setIsTyping(data.is_typing);
        if (data.is_typing) {
            setStreamingContent(""); // Reset buffer on new typing start
        }
      }
      
      // 3. Token Stream
      else if (data.type === 'playground_stream') {
        setStreamingContent(prev => prev + data.content);
      }

      // 4. Debug Info
      else if (data.type === 'playground_debug') {
        setDebugInfo(data);
      }
    });

    return () => unsub();
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent, isTyping]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isTyping) return;

    const text = inputText;
    setInputText("");
    
    // Clear previous debug info on new turn
    setDebugInfo(null);

    await api.post('/playground/message', { sender, text });
  };

  return (
    <div className="h-[calc(100vh-140px)] flex gap-4 overflow-hidden">
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white dark:bg-[#1e1e1e] rounded-2xl shadow-xl border border-gray-200 dark:border-[#333] overflow-hidden">
        
        {/* Header */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-[#252526] border-b border-gray-200 dark:border-[#333] flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400">
              <Sparkles size={20} />
            </div>
            <div>
              <h2 className="font-bold text-gray-900 dark:text-white">Chat Playground</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">TESTING ENVIRONMENT</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Sender Selector */}
            <div className="flex items-center gap-2 bg-white dark:bg-[#181818] border border-gray-200 dark:border-[#444] rounded-lg px-3 py-1.5">
              <User size={14} className="text-gray-400" />
              <select 
                value={sender} 
                onChange={(e) => setSender(e.target.value)}
                className="bg-transparent border-none outline-none text-xs font-bold w-32 cursor-pointer dark:text-gray-200"
              >
                <option value="TestUser">TestUser</option>
                {profiles.map(p => (
                   <option key={p.handle} value={p.handle}>{p.handle} ({p.name})</option>
                ))}
              </select>
            </div>
            
            {/* Debug Toggle */}
            <button 
              onClick={() => setShowDebug(!showDebug)}
              className={`p-2 rounded-lg transition-colors ${showDebug ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/50' : 'hover:bg-gray-100 dark:hover:bg-[#333] text-gray-500'}`}
            >
              <Terminal size={18} />
            </button>
          </div>
        </div>

        {/* Messages List */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50 space-y-4">
              <Bot size={48} />
              <p className="text-sm font-mono max-w-xs">SEND A MESSAGE TO START SIMULATING CONVERSATION WITH FERN.</p>
            </div>
          )}
          
          {/* History */}
          {messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'assistant' ? 'items-start' : 'items-end'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-sm ${
                msg.role === 'assistant' 
                  ? 'bg-purple-50 dark:bg-purple-900/20 text-gray-900 dark:text-purple-100 border border-purple-100 dark:border-purple-900/30' 
                  : 'bg-green-500 text-white'
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                    {msg.sender}
                  </span>
                  <span className="text-[10px] opacity-50">{msg.time}</span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              </div>
            </div>
          ))}

          {/* Streaming / Typing Indicator */}
          {isTyping && (
             <div className="flex flex-col items-start animate-in fade-in slide-in-from-bottom-2 duration-300">
               <div className="max-w-[80%] rounded-2xl px-4 py-3 shadow-sm bg-purple-50 dark:bg-purple-900/20 text-gray-900 dark:text-purple-100 border border-purple-100 dark:border-purple-900/30">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Fern</span>
                    <span className="text-[10px] opacity-50">Typing...</span>
                  </div>
                  {streamingContent ? (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{streamingContent}<span className="inline-block w-1.5 h-4 ml-1 bg-purple-500 animate-pulse align-middle"></span></p>
                  ) : (
                      <div className="flex gap-1 h-5 items-center">
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce"></div>
                      </div>
                  )}
               </div>
             </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 bg-gray-50 dark:bg-[#252526] border-t border-gray-200 dark:border-[#333]">
          <form onSubmit={sendMessage} className="relative flex items-center gap-2">
            <input 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder={`Message as ${sender}...`}
              className="flex-1 bg-white dark:bg-[#181818] border border-gray-200 dark:border-[#444] rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-purple-500 outline-none pr-12 transition-all"
            />
            <button 
              type="submit"
              disabled={isTyping || !inputText.trim()}
              className="absolute right-2 p-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:hover:bg-purple-600"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>

      {/* Right Sidebar: Cortex Debug Panel */}
      {showDebug && (
        <div className="w-80 bg-white dark:bg-[#1e1e1e] rounded-2xl shadow-xl border border-gray-200 dark:border-[#333] flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-[#333] bg-gray-50 dark:bg-[#252526] flex items-center gap-2">
                <Brain size={16} className="text-purple-500"/>
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">Cortex Debug</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
                {!debugInfo ? (
                    <div className="text-center py-10 opacity-40 space-y-2">
                        <Activity size={32} className="mx-auto"/>
                        <p className="text-xs font-mono">WAITING FOR GENERATION DATA...</p>
                    </div>
                ) : (
                    <>
                        {/* Stats */}
                        <div className="grid grid-cols-2 gap-2">
                            <div className="p-3 bg-gray-50 dark:bg-[#252526] rounded-lg border border-gray-100 dark:border-[#333]">
                                <p className="text-[10px] text-gray-500 uppercase">Speed</p>
                                <p className="text-lg font-mono font-bold text-green-500">{(debugInfo.tps || 0).toFixed(1)} t/s</p>
                            </div>
                            <div className="p-3 bg-gray-50 dark:bg-[#252526] rounded-lg border border-gray-100 dark:border-[#333]">
                                <p className="text-[10px] text-gray-500 uppercase">Memory</p>
                                <p className="text-xs font-mono font-bold text-blue-500 mt-1">{debugInfo.mem_usage}</p>
                            </div>
                        </div>

                        {/* RAG Facts */}
                        <div>
                            <div className="flex items-center gap-2 mb-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                <Database size={12}/>
                                <span>Retrieved Facts</span>
                            </div>
                            <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-900/20 rounded-lg p-3">
                                {debugInfo.rag_info?.facts && debugInfo.rag_info.facts.length > 0 ? (
                                    <ul className="space-y-1">
                                        {debugInfo.rag_info.facts.map((f, i) => (
                                            <li key={i} className="text-xs text-yellow-800 dark:text-yellow-200 flex gap-2">
                                                <span className="opacity-50">•</span>
                                                {f}
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="text-xs text-gray-400 italic">No facts retrieved.</p>
                                )}
                            </div>
                        </div>

                         {/* Master Scenarios */}
                         <div>
                            <div className="flex items-center gap-2 mb-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                <Activity size={12}/>
                                <span>Active Scenario</span>
                            </div>
                            <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/20 rounded-lg p-3">
                                {debugInfo.rag_info?.scenarios && debugInfo.rag_info.scenarios.length > 0 ? (
                                     <p className="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
                                        {debugInfo.rag_info.scenarios[0]}
                                     </p>
                                ) : (
                                    <p className="text-xs text-gray-400 italic">No master scenario active.</p>
                                )}
                            </div>
                        </div>

                        {/* System Prompt Log */}
                        <div>
                             <div className="flex items-center gap-2 mb-2 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                <Terminal size={12}/>
                                <span>Prompt Log</span>
                            </div>
                            <pre className="text-[10px] font-mono bg-gray-900 text-gray-400 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap max-h-60 custom-scrollbar">
                                {debugInfo.prompt_log || "No log available."}
                            </pre>
                        </div>
                    </>
                )}
            </div>
        </div>
      )}

    </div>
  );
}
