import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import { Database, Trash2, Search, Network, Grid, FileText, CheckCircle } from 'lucide-react';
import ForceGraph3D from 'react-force-graph-3d';

export default function Memories() {
  const [memories, setMemories] = useState([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('grid'); // 'grid' | 'graph'
  const [activeTab, setActiveTab] = useState('facts'); // 'facts' | 'logs'
  const fgRef = useRef();

  useEffect(() => {
    fetchMemories();
  }, []);

  useEffect(() => {
    if (view === 'graph') {
        fetchGraph();
    }
  }, [view]);

  const fetchMemories = async () => {
    setLoading(true);
    const res = await api.get('/memories');
    if (res && res.memories) {
       setMemories(res.memories);
    }
    setLoading(false);
  };

  const fetchGraph = async () => {
      const res = await api.get('/memories/graph');
      if (res && res.nodes) {
          setGraphData(res);
      }
  };

  const deleteMemory = async (id) => {
    if (!confirm("Delete this memory permanently?")) return;
    await api.delete(`/memories/${id}`);
    setMemories(prev => prev.filter(m => m.id !== id));
    if (view === 'graph') fetchGraph();
  };

  // Filter Logic
  const filtered = memories.filter(m => {
      // 1. Text Search
      const matchesSearch = m.text && m.text.toLowerCase().includes(search.toLowerCase());
      if (!matchesSearch) return false;

      // 2. Tab Filter
      if (activeTab === 'facts') {
          // Show strict_fact OR generic unknown (legacy)
          return m.meta?.source === 'strict_fact' || m.meta?.source === 'fact_extraction';
      } else {
          // Show log_entry
          return m.meta?.source === 'log_entry';
      }
  });

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
         <div>
            <h2 className="text-xl font-bold text-text dark:text-[#f5f5f5] flex items-center gap-2">
               <Database className="text-blue-500" />
               Memory Bank
            </h2>
            <p className="text-sm text-text-secondary dark:text-[#a8a8a8]">
                {activeTab === 'facts' ? "Atomic verified facts." : "Narrative logbook entries."}
            </p>
         </div>
         
         <div className="flex items-center gap-3 w-full md:w-auto">
            {/* View Toggle */}
            <div className="flex bg-gray-100 dark:bg-[#252526] p-1 rounded-lg">
                <button 
                    onClick={() => setView('grid')}
                    className={`p-2 rounded-md transition-all ${view === 'grid' ? 'bg-white dark:bg-[#333] shadow text-blue-500' : 'text-gray-500'}`}
                >
                    <Grid size={18} />
                </button>
                <button 
                    onClick={() => setView('graph')}
                    className={`p-2 rounded-md transition-all ${view === 'graph' ? 'bg-white dark:bg-[#333] shadow text-purple-500' : 'text-gray-500'}`}
                >
                    <Network size={18} />
                </button>
            </div>

            <div className="relative flex-1 md:w-64">
                <Search className="absolute left-3 top-2.5 text-text-tertiary" size={16} />
                <input 
                type="text" 
                placeholder="Search..." 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-10 bg-white dark:bg-[#262626] dark:text-white dark:border-[#363636] w-full"
                />
            </div>
         </div>
      </div>

      {/* Tabs */}
      {view === 'grid' && (
          <div className="flex gap-4 border-b border-border dark:border-[#363636]">
              <button 
                onClick={() => setActiveTab('facts')}
                className={`pb-2 px-2 text-sm font-medium flex items-center gap-2 ${activeTab === 'facts' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-text-secondary'}`}
              >
                  <CheckCircle size={14} /> Verified Facts
              </button>
              <button 
                onClick={() => setActiveTab('logs')}
                className={`pb-2 px-2 text-sm font-medium flex items-center gap-2 ${activeTab === 'logs' ? 'text-orange-500 border-b-2 border-orange-500' : 'text-text-secondary'}`}
              >
                  <FileText size={14} /> History Logs
              </button>
          </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden relative bg-surface dark:bg-[#1e1e1e] border border-border dark:border-[#363636] rounded-xl">
         
         {view === 'grid' ? (
             <div className="h-full overflow-y-auto p-4 custom-scrollbar">
                {loading && memories.length === 0 && (
                    <div className="text-center text-text-secondary py-10">Accessing Neural Database...</div>
                )}
                
                {!loading && filtered.length === 0 && (
                    <div className="text-center text-text-tertiary py-10">No memories found in this category.</div>
                )}

                <div className={`grid gap-4 ${activeTab === 'facts' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1 lg:grid-cols-2'}`}>
                    {filtered.map((mem) => (
                    <div key={mem.id} className="card p-4 hover:shadow-md transition-shadow group relative bg-white dark:bg-[#252526] border border-gray-200 dark:border-[#333]">
                        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button 
                            onClick={() => deleteMemory(mem.id)}
                            className="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 text-text-tertiary hover:text-red-500 rounded"
                            title="Delete Memory"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                        
                        <div className="flex items-center gap-2 mb-3">
                            <div className={`text-xs font-mono px-2 py-1 rounded ${activeTab === 'facts' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400'}`}>
                                {mem.meta?.source || "unknown"}
                            </div>
                            <span className="text-[10px] text-text-tertiary">
                                {mem.id.substring(0,6)}
                            </span>
                            {mem.meta?.timestamp && (
                                <span className="text-[10px] text-text-tertiary ml-auto">
                                    {new Date(parseFloat(mem.meta.timestamp) * 1000).toLocaleDateString()}
                                </span>
                            )}
                        </div>
                        
                        <p className={`text-sm text-text dark:text-[#e0e0e0] leading-relaxed break-words ${activeTab === 'logs' ? 'whitespace-pre-wrap font-mono text-xs' : ''}`}>
                            {mem.text}
                        </p>
                    </div>
                    ))}
                </div>
             </div>
         ) : (
             <div className="h-full w-full bg-black">
                 {graphData.nodes.length > 0 ? (
                     <ForceGraph3D
                        ref={fgRef}
                        graphData={graphData}
                        nodeLabel="text"
                        nodeAutoColorBy="group"
                        nodeRelSize={6}
                        linkOpacity={0.3}
                        linkWidth={1}
                        backgroundColor="#000000"
                        onNodeClick={node => {
                            // Aim at node on click
                            const distance = 40;
                            const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                            fgRef.current.cameraPosition(
                                { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, 
                                node, 
                                3000
                            );
                        }}
                     />
                 ) : (
                     <div className="flex h-full items-center justify-center text-gray-500">
                         {loading ? "Calculating Vector Space..." : "Not enough data for 3D Graph."}
                     </div>
                 )}
             </div>
         )}
      </div>
    </div>
  );
}