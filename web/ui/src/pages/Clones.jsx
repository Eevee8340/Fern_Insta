import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { User, CheckCircle, RefreshCw, Eye, X } from 'lucide-react';
import clsx from 'clsx';

const PromptModal = ({ handle, prompt, onClose }) => {
  if (!handle) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-[#1e1e1e] rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col border border-gray-200 dark:border-[#363636]">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-[#363636]">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <User size={18} className="text-blue-500"/> 
            {handle}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-[#333] rounded-full transition-colors text-gray-500">
            <X size={20} />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">
           <pre className="whitespace-pre-wrap font-mono text-xs text-gray-600 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-[#121212] p-4 rounded-lg border border-gray-100 dark:border-[#262626]">
             {prompt || "No prompt data available."}
           </pre>
        </div>
      </div>
    </div>
  );
};

export default function Clones() {
  const [clones, setClones] = useState([]);
  const [prompts, setPrompts] = useState({});
  const [active, setActive] = useState(null);
  const [loading, setLoading] = useState(false);
  const [viewingClone, setViewingClone] = useState(null);

  const fetchClones = async () => {
    const res = await api.get('/clones');
    if (res) {
      setClones(res.clones || []);
      setPrompts(res.prompts || {});
      setActive(res.active);
    }
  };

  useEffect(() => { fetchClones(); }, []);

  const activate = async (handle) => {
    setLoading(true);
    await api.post('/clones/activate', { handle });
    await fetchClones();
    setLoading(false);
  };

  const reset = async () => {
    setLoading(true);
    await api.post('/clones/reset', {});
    await fetchClones();
    setLoading(false);
  };

  return (
    <div className="space-y-6 relative">
      <PromptModal 
        handle={viewingClone} 
        prompt={prompts[viewingClone]} 
        onClose={() => setViewingClone(null)} 
      />

      <div className="flex justify-between items-center mb-4">
        <div>
           <h2 className="text-xl font-bold text-text dark:text-[#f5f5f5]">Select Personality</h2>
           <p className="text-sm text-text-secondary dark:text-[#a8a8a8]">Choose a persona for the AI to mimic.</p>
        </div>
        <button onClick={reset} disabled={loading} className="btn-secondary text-xs dark:text-[#e0e0e0] dark:border-[#363636] dark:hover:bg-[#2c2c2c]">
          <RefreshCw className={clsx("inline mr-2 w-3 h-3", loading && "animate-spin")}/>
          Reset to Default
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {clones.map((cloneObj) => {
          // Handle both old (string) and new (object) API formats for compatibility
          const handle = cloneObj.handle || cloneObj; 
          const pfp = cloneObj.pfp_url;
          
          const isActive = active === handle;
          const displayName = (typeof handle === 'string') ? handle.replace(/^@+/, '') : "Unknown";

          return (
            <div key={handle} className={clsx(
              "card p-6 transition-all relative overflow-hidden group border",
              isActive 
                 ? "border-primary shadow-md ring-1 ring-primary bg-surface dark:bg-[#1e1e1e]" 
                 : "border-border dark:border-[#363636] hover:border-gray-300 dark:hover:border-[#505050] bg-surface dark:bg-[#1e1e1e]"
            )}>
               {/* Top Actions */}
               <div className="absolute top-4 right-4 flex gap-2">
                  <button 
                     onClick={() => setViewingClone(handle)}
                     className="p-1.5 rounded-full text-text-tertiary hover:bg-gray-100 dark:hover:bg-[#333] hover:text-primary transition-colors"
                     title="View System Prompt"
                  >
                     <Eye size={18} />
                  </button>
                  {isActive && (
                     <div className="text-primary pt-1">
                        <CheckCircle size={20} fill="#0095f6" className="text-white dark:text-[#1e1e1e]" />
                     </div>
                  )}
               </div>
               
               <div className="flex flex-col items-center mb-4 pt-2">
                 <div className="w-20 h-20 rounded-full bg-gray-100 dark:bg-[#2c2c2c] mb-4 overflow-hidden border border-border dark:border-[#363636]">
                    <img 
                        src={pfp || `https://ui-avatars.com/api/?name=${displayName}&size=128&background=random`} 
                        alt={displayName} 
                        className="w-full h-full object-cover"
                    />
                 </div>
                 <h3 className="font-bold text-lg text-text dark:text-[#f5f5f5]">{displayName}</h3>
                 <span className={clsx(
                    "text-xs px-2 py-1 rounded-full mt-2",
                    isActive 
                      ? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                      : "text-text-secondary bg-gray-100 dark:bg-[#2c2c2c] dark:text-[#a8a8a8]"
                 )}>
                    {isActive ? "Currently Active" : "Available"}
                 </span>
               </div>

               <button 
                 onClick={() => activate(handle)}
                 disabled={isActive || loading}
                 className={clsx(
                   "w-full py-2 rounded-lg font-semibold text-sm transition-colors", 
                   isActive 
                     ? "bg-gray-100 text-text-secondary cursor-default dark:bg-[#2c2c2c] dark:text-[#737373]" 
                     : "bg-primary text-white hover:bg-primary-hover shadow-sm"
                 )}
               >
                 {isActive ? "Selected" : "Switch Profile"}
               </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}