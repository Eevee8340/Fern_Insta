import React, { useEffect, useState } from 'react';
import { api, socket } from '../services/api';
import { Activity, Database, Clock, Zap, RefreshCw, Camera, MessageSquare, Hash, ExternalLink, User, X, Eye } from 'lucide-react';
import clsx from 'clsx';

const StatItem = ({ label, children }) => (
  <div className="flex flex-col h-full justify-between">
    <span className="text-text-secondary text-xs font-semibold uppercase tracking-wide mb-2">{label}</span>
    {children}
  </div>
);

const ViewPromptModal = ({ prompt, onClose }) => {
   if (!prompt) return null;
   return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
         <div className="bg-surface w-full max-w-2xl rounded-xl shadow-2xl border border-border flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between p-4 border-b border-border">
               <h3 className="font-semibold text-lg flex items-center gap-2">
                  <User size={18} /> System Persona
               </h3>
               <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full transition-colors">
                  <X size={20} />
               </button>
            </div>
            <div className="p-6 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-text-secondary leading-relaxed custom-scrollbar">
               {prompt}
            </div>
         </div>
      </div>
   );
}

const ViewTracesModal = ({ onClose }) => {
    const [traces, setTraces] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTraces = async () => {
            const data = await api.get('/traces');
            if (data && data.traces) {
                // Show newest first
                setTraces(data.traces.reverse());
            }
            setLoading(false);
        };
        fetchTraces();
        const interval = setInterval(fetchTraces, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
           <div className="bg-surface w-full max-w-4xl rounded-xl shadow-2xl border border-border flex flex-col h-[85vh]">
              <div className="flex items-center justify-between p-4 border-b border-border">
                 <h3 className="font-semibold text-lg flex items-center gap-2">
                    <Zap size={18} className="text-yellow-500" /> System Traces (Performance)
                 </h3>
                 <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full transition-colors">
                    <X size={20} />
                 </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4 custom-scrollbar bg-gray-50/50">
                 {loading ? (
                     <div className="flex items-center justify-center h-full text-text-tertiary">
                         <RefreshCw size={24} className="animate-spin" />
                     </div>
                 ) : traces.length === 0 ? (
                     <div className="flex items-center justify-center h-full text-text-tertiary font-mono italic">
                         NO TRACES RECORDED
                     </div>
                 ) : (
                     <div className="space-y-4">
                         {traces.map((trace) => (
                             <div key={trace.trace_id} className="bg-white border border-border rounded-lg overflow-hidden shadow-sm">
                                 <div className="bg-gray-100/50 px-3 py-2 border-b border-border flex items-center justify-between text-xs font-mono">
                                     <div className="flex items-center gap-4">
                                         <span className="font-bold text-blue-600">ID: {trace.trace_id}</span>
                                         <span className="text-text-tertiary">{trace.source}</span>
                                         <span className="text-text-tertiary">{new Date(trace.start_time * 1000).toLocaleTimeString()}</span>
                                     </div>
                                     <div className="font-bold text-text">
                                         Total: {(trace.total_duration * 1000).toFixed(1)}ms
                                     </div>
                                 </div>
                                 <div className="p-3 space-y-1">
                                     {trace.events.map((event, idx) => (
                                         <div key={idx} className="flex items-center gap-3 text-[11px] font-mono group">
                                             <div className="w-16 text-right text-text-tertiary shrink-0">
                                                 +{(event.elapsed * 1000).toFixed(1)}ms
                                             </div>
                                             <div className="w-2 h-2 rounded-full bg-border group-hover:bg-blue-400 shrink-0"></div>
                                             <div className="flex-1 flex items-center justify-between">
                                                 <span className="font-medium text-text-secondary">{event.event}</span>
                                                 {event.delta > 0.005 && (
                                                     <span className={clsx(
                                                         "px-1.5 py-0.5 rounded text-[9px] font-bold",
                                                         event.delta > 0.5 ? "bg-red-100 text-red-600" : "bg-yellow-100 text-yellow-600"
                                                     )}>
                                                         STEP: {(event.delta * 1000).toFixed(0)}ms
                                                     </span>
                                                 )}
                                             </div>
                                             {Object.keys(event.data).length > 0 && (
                                                 <div className="text-[10px] text-text-tertiary italic max-w-[200px] truncate">
                                                     {JSON.stringify(event.data)}
                                                 </div>
                                             )}
                                         </div>
                                     ))}
                                 </div>
                             </div>
                         ))}
                     </div>
                 )}
              </div>
           </div>
        </div>
    );
};

export default function Dashboard() {
  const [stats, setStats] = useState({
    msg_count: 0,
    context_limit: 4096,
    last_sender: "None",
    is_sleeping: false,
    is_typing: false,
    tps: 0.0,
    mem: "0/0",
    thread_name: "Loading...",
    persona_name: "Fern",
    system_prompt: ""
  });
  
  const [groups, setGroups] = useState({});
  const [switching, setSwitching] = useState(null);
  const [visionTs, setVisionTs] = useState(Date.now());
  const [showPrompt, setShowPrompt] = useState(false);
  const [showTraces, setShowTraces] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      const data = await api.get('/status');
      if (data) setStats(prev => ({ ...prev, ...data }));
    };

    const fetchGroups = async () => {
      const data = await api.get('/groups');
      if (data && data.groups) setGroups(data.groups);
    };

    fetchStats();
    fetchGroups();
    
    const interval = setInterval(() => {
      setVisionTs(Date.now());
      fetchStats();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleSwitch = async (name, threadId) => {
    setSwitching(name);
    await api.post('/groups/switch', { thread_id: threadId });
    setTimeout(() => setSwitching(null), 3000);
  };

  // Helper for Status UI
  const getStatusUI = () => {
     if (stats.is_typing) return { color: "bg-blue-500", text: "Typing...", pulse: true };
     if (stats.is_sleeping) return { color: "bg-yellow-400", text: "Sleeping", pulse: false };
     return { color: "bg-green-500", text: "Active", pulse: true };
  };

  const statusUI = getStatusUI();
  
  // Parse Memory Usage for Progress Bar
  const rawMem = stats.mem || "0/0";
  let [curStr, maxStr] = rawMem.replace(/[~]/g, "").split("/");
  
  let currentTokens = parseFloat(curStr) || 0;
  let maxTokens = parseFloat(maxStr) || stats.context_limit || 4096;
  
  const memPercent = maxTokens > 0 ? (currentTokens / maxTokens) * 100 : 0;
  const safeMemPercent = isNaN(memPercent) ? 0 : memPercent;

  return (
    <div className="space-y-8">
      {showPrompt && <ViewPromptModal prompt={stats.system_prompt} onClose={() => setShowPrompt(false)} />}
      {showTraces && <ViewTracesModal onClose={() => setShowTraces(false)} />}
      
      {/* Header */}
      <div className="flex items-center justify-between">
         <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]">
               <div className="w-full h-full rounded-full bg-surface p-1">
                  <img src="/assets/icon.png" className="w-full h-full rounded-full bg-gray-200 object-cover" onError={(e) => e.target.src='https://ui-avatars.com/api/?name=Fern+Nexus&background=random'} />
               </div>
            </div>
            <div>
               <h1 className="text-xl font-light tracking-tight">Fern <span className="text-blue-500 text-sm ml-1">✓</span></h1>
               <div className="flex items-center gap-3 text-sm mt-1">
                  <span className="font-semibold">{stats.msg_count} <span className="font-normal text-text-secondary">messages</span></span>
                  <span className="text-border">|</span>
                  <div className="flex items-center gap-2">
                     <div className={clsx("w-2 h-2 rounded-full", statusUI.color, statusUI.pulse && "animate-pulse")}></div>
                     <span className="font-medium text-text-secondary">{statusUI.text}</span>
                  </div>
               </div>
            </div>
         </div>
      </div>

      {/* Stats Grid (4 Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pb-8 border-b border-border">
          {/* Card 1: Active Thread */}
          <div className="card p-5 relative overflow-hidden group">
              <StatItem label="Active Thread">
                 <div className="flex items-center gap-2 truncate">
                    <Hash size={18} className="text-text-tertiary" />
                    <span className="text-xl font-bold text-text truncate" title={stats.thread_name}>{stats.thread_name || "Unknown"}</span>
                 </div>
              </StatItem>
          </div>

          {/* Card 2: System Load */}
          <div className="card p-5">
              <StatItem label="System Load">
                 <div className="space-y-3">
                    <div className="flex items-end gap-1">
                       <span className="text-2xl font-bold text-text">{stats.tps.toFixed(1)}</span>
                       <span className="text-xs text-text-tertiary mb-1.5">T/s</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
                       <div 
                           className={clsx("h-full rounded-full transition-all duration-500", safeMemPercent > 80 ? "bg-red-500" : "bg-blue-500")} 
                           style={{ width: `${Math.min(safeMemPercent, 100)}%` }}
                        ></div>
                    </div>
                    <div className="flex justify-between text-[10px] text-text-tertiary uppercase font-mono">
                       <span>Context</span>
                       <span>{Math.round(safeMemPercent)}%</span>
                    </div>
                 </div>
              </StatItem>
          </div>

          {/* Card 3: Last Interaction */}
          <div className="card p-5">
              <StatItem label="Last Interaction">
                 <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-text-tertiary overflow-hidden border border-border">
                       {stats.last_sender_pfp ? (
                          <img 
                            src={stats.last_sender_pfp} 
                            alt="" 
                            className="w-full h-full object-cover" 
                            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                          />
                       ) : null}
                       <div className="w-full h-full flex items-center justify-center bg-gray-100" style={{ display: stats.last_sender_pfp ? 'none' : 'flex' }}>
                          <User size={20} />
                       </div>
                    </div>
                    <div className="flex flex-col overflow-hidden">
                       <span className="font-bold text-text truncate" title={stats.last_sender}>{stats.last_sender}</span>
                       <span className="text-[10px] text-blue-500 font-medium truncate">{stats.last_sender_title || "Resident"}</span>
                    </div>
                 </div>
              </StatItem>
          </div>

          {/* Card 4: Persona */}
          <div className="card p-5">
              <StatItem label="Persona">
                 <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                       <span className="text-lg font-bold text-text truncate max-w-[120px]" title={stats.persona_name}>{stats.persona_name}</span>
                       <span className="text-[10px] text-text-tertiary uppercase tracking-wider">Default</span>
                    </div>
                    <button 
                       onClick={() => setShowPrompt(true)}
                       className="p-2 hover:bg-gray-100 rounded-lg text-text-secondary transition-colors group"
                       title="View System Prompt"
                    >
                       <Eye size={18} className="group-hover:text-blue-500 transition-colors"/>
                    </button>
                 </div>
              </StatItem>
          </div>
      </div>

      {/* Content Area (Vision) */}
      <div>
         <div className="flex items-center justify-between mb-4">
            <div className="flex gap-6 border-t border-black md:border-t-0 pt-4 md:pt-0">
               <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-text border-t border-text -mt-[17px] pt-4">
                  <Camera size={14} /> Live Vision
               </span>
            </div>
            <div className="flex items-center gap-4">
               <button onClick={() => setShowTraces(true)} className="text-text-secondary hover:text-blue-500 text-sm flex items-center gap-1 transition-colors">
                  <Activity size={14}/> Debug Traces
               </button>
               <button onClick={() => api.post('/browser/restart')} className="text-text-secondary hover:text-text text-sm flex items-center gap-1">
                  <RefreshCw size={14}/> Refresh Browser
               </button>
            </div>
         </div>

         <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
             {/* Live Vision Area - Takes up 75% of space */}
             <div className="lg:col-span-3 space-y-3">
                <div className="aspect-video bg-black rounded-xl overflow-hidden relative shadow-lg border border-border/50 group">
                    <img 
                      src={`/screenshot?t=${visionTs}`} 
                      className="w-full h-full object-contain"
                      alt="Live Feed"
                    />
                    <div className="absolute top-4 right-4 bg-red-600/90 backdrop-blur text-white text-[10px] font-bold px-2 py-0.5 rounded shadow-sm animate-pulse">
                       LIVE
                    </div>
                </div>
                <div className="flex justify-between items-center px-1">
                   <div className="text-xs text-text-tertiary flex items-center gap-2">
                      <Camera size={12} />
                      <span>Vision Feed (16:9)</span>
                   </div>
                </div>
             </div>
             
             {/* Quick Thread Switcher - Compact Sidebar */}
             <div className="lg:col-span-1 flex flex-col h-full">
                <div className="bg-surface border border-border rounded-xl flex flex-col h-full shadow-sm overflow-hidden">
                   <div className="p-4 border-b border-border flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                         Threads
                      </h3>
                      {switching && <RefreshCw size={14} className="animate-spin text-primary"/>}
                   </div>
                   
                   <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                      {Object.entries(groups).map(([name, id]) => (
                         <button 
                            key={id}
                            onClick={() => handleSwitch(name, id)}
                            disabled={switching === name}
                            title={id}
                            className={clsx(
                               "w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-all duration-200 group relative",
                               switching === name 
                                  ? "bg-primary/10 text-primary" 
                                  : "hover:bg-text-tertiary/10 text-text-secondary hover:text-text"
                            )}
                         >
                            <div className={clsx(
                               "w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold transition-all duration-200",
                               switching === name 
                                  ? "bg-primary text-white shadow-sm" 
                                  : "bg-text-tertiary/20 text-text-secondary group-hover:bg-text-tertiary/30"
                            )}>
                               {name.substring(0, 2).toUpperCase()}
                            </div>
                            
                            <span className="text-sm font-medium truncate">{name}</span>
                            
                            {switching === name && (
                               <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></div>
                            )}
                         </button>
                      ))}
                   </div>
                </div>
             </div>
         </div>
      </div>

    </div>
  );
}