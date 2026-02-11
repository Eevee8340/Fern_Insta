import React, { useEffect, useState } from 'react';
import { api, socket } from '../services/api';
import { Brain, RefreshCw, Eye, FileText, User, Book, MessageSquare, Database, AlertCircle, Terminal } from 'lucide-react';

export default function Context() {
  const [rawContext, setRawContext] = useState("");
  const [debugData, setDebugData] = useState({});
  const [viewMode, setViewMode] = useState("pretty"); // 'pretty' | 'raw'
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchContext();
    const unsub = socket.subscribe((data) => {
       if (data.type === 'meta') {
           if (data.prompt_log) setRawContext(data.prompt_log);
           if (data.rag_info) setDebugData(data.rag_info);
       }
    });
    return () => unsub();
  }, []);

  const fetchContext = async () => {
    setLoading(true);
    const res = await api.get('/context');
    if (res) {
        if (res.context) setRawContext(res.context);
        if (res.rag) setDebugData(res.rag);
    }
    setLoading(false);
  };

  const Section = ({ title, icon: Icon, children, color = "purple", isEmpty = false, height = "auto" }) => (
    <div className={`border border-border dark:border-[#2d2d2d] rounded-lg overflow-hidden flex flex-col bg-bg-card shadow-sm ${isEmpty ? 'opacity-60' : ''}`}>
        <div className={`bg-${color}-500/5 px-3 py-2 border-b border-border dark:border-[#2d2d2d] flex items-center justify-between`}>
            <div className="flex items-center gap-2">
                <Icon size={14} className={`text-${color}-500`} />
                <h3 className="text-[10px] font-bold text-text uppercase tracking-widest">{title}</h3>
            </div>
            {isEmpty && <span className="text-[9px] font-medium text-text-tertiary italic">Empty</span>}
        </div>
        <div className={`p-3 overflow-auto custom-scrollbar`} style={{ height }}>
            {children}
        </div>
    </div>
  );

  const EmptyState = ({ message }) => (
      <div className="flex items-center gap-2 text-text-tertiary italic py-1 text-[11px]">
          <AlertCircle size={12} />
          <span>{message}</span>
      </div>
  );

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-3 max-w-[1600px] mx-auto w-full px-2 pb-2">
      {/* Compact Header */}
      <div className="flex justify-between items-center bg-bg-card px-4 py-2 rounded-lg border border-border shadow-sm">
         <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
                <Brain className="text-purple-500" size={18} />
            </div>
            <div>
                <h2 className="text-sm font-bold text-text leading-tight">Neural Workspace</h2>
                <p className="text-[10px] text-text-secondary leading-tight">Active RAG Retrieval & Prompt Logic</p>
            </div>
         </div>
         
         <div className="flex items-center gap-2">
             <div className="bg-bg-page border border-border rounded-md p-0.5 flex">
                 <button 
                    onClick={() => setViewMode("pretty")}
                    className={`px-3 py-1 text-[10px] font-bold rounded flex items-center gap-1.5 transition-all ${viewMode === 'pretty' ? 'bg-purple-500 text-white shadow-sm' : 'text-text-secondary hover:bg-hover'}`}
                 >
                    <Eye size={12} /> Visual
                 </button>
                 <button 
                    onClick={() => setViewMode("raw")}
                    className={`px-3 py-1 text-[10px] font-bold rounded flex items-center gap-1.5 transition-all ${viewMode === 'raw' ? 'bg-purple-500 text-white shadow-sm' : 'text-text-secondary hover:bg-hover'}`}
                 >
                    <FileText size={12} /> Raw
                 </button>
             </div>
             <button 
                onClick={fetchContext} 
                disabled={loading} 
                className="p-1.5 hover:bg-hover border border-border rounded-md text-text-secondary transition-colors"
             >
                <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
             </button>
         </div>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'raw' ? (
            <div className="card h-full flex flex-col shadow-lg overflow-hidden border border-border bg-[#1e1e1e]">
                <div className="bg-[#252526] border-b border-[#2d2d2d] px-3 py-1.5 flex items-center gap-2">
                    <Terminal size={12} className="text-gray-400" />
                    <span className="text-[10px] font-mono text-gray-400 uppercase tracking-tighter">active_inference_payload.log</span>
                </div>
                <div className="flex-1 overflow-auto p-4 md:p-8">
                    <pre className="whitespace-pre-wrap font-mono text-[11px] text-gray-300 leading-relaxed selection:bg-purple-500 selection:text-white">
                        {rawContext || "// No active context. Send a message to the bot."}
                    </pre>
                </div>
            </div>
        ) : (
            <div className="h-full flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
                
                {/* Top Row: Trigger */}
                <Section title="Last Trigger" icon={MessageSquare} color="purple" isEmpty={!debugData.query}>
                    {debugData.query ? (
                        <div className="flex items-start gap-3">
                            <div className="mt-1 w-1 h-3 bg-purple-500 rounded-full shrink-0" />
                            <p className="text-xs text-text font-medium leading-normal italic">
                                {debugData.query}
                            </p>
                        </div>
                    ) : <EmptyState message="Waiting for input..." />}
                </Section>

                {/* Middle Content: Split Grid */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 overflow-hidden">
                    
                    {/* Left Col: Core Logic (4/12) */}
                    <div className="lg:col-span-4 flex flex-col gap-3 overflow-hidden">
                        <Section title="System Core" icon={User} color="blue" height="100%">
                            <pre className="whitespace-pre-wrap font-mono text-[10px] text-text-secondary leading-normal">
                                {debugData.system || "Loading profile..."}
                            </pre>
                        </Section>
                    </div>

                    {/* Right Col: RAG Elements (8/12) */}
                    <div className="lg:col-span-8 flex flex-col gap-3 overflow-hidden">
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 shrink-0">
                            {/* Facts */}
                            <Section title="Verified Facts" icon={Database} color="green" isEmpty={!debugData.facts?.length} height="180px">
                                {debugData.facts && debugData.facts.length > 0 ? (
                                    <div className="space-y-1.5">
                                        {debugData.facts.map((fact, i) => (
                                            <div key={i} className="flex gap-2 items-start bg-green-500/5 border border-green-500/10 rounded p-2 transition-colors">
                                                <div className="mt-1.5 w-1 h-1 rounded-full bg-green-500 shrink-0" />
                                                <span className="text-[10px] text-text-secondary leading-tight">{fact}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : <EmptyState message="No facts recalled." />}
                            </Section>

                            {/* Lore */}
                            <Section title="Lore & Slang" icon={Book} color="yellow" isEmpty={!debugData.lore} height="180px">
                                {debugData.lore ? (
                                    <div className="text-[10px] font-mono text-text-secondary bg-yellow-500/5 border border-yellow-500/10 p-2 rounded leading-normal whitespace-pre-wrap">
                                        {debugData.lore}
                                    </div>
                                ) : <EmptyState message="No lore detected." />}
                            </Section>
                        </div>

                        {/* Narrative Logs (Flexible Fill) */}
                        <Section title="Narrative Context (Long-Term)" icon={FileText} color="orange" isEmpty={!debugData.logs?.length} height="100%">
                            {debugData.logs && debugData.logs.length > 0 ? (
                                <div className="space-y-3">
                                    {debugData.logs.map((log, i) => (
                                        <div key={i} className="bg-orange-500/5 border border-orange-500/10 rounded-lg p-3 text-[11px] font-mono text-text-secondary leading-relaxed shadow-sm whitespace-pre-wrap">
                                            {log}
                                        </div>
                                    ))}
                                </div>
                            ) : <EmptyState message="No narrative logs recalled." />}
                        </Section>
                    </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}