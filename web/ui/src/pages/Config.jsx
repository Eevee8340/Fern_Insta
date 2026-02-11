import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { 
  Save, AlertTriangle, Cpu, Zap, Activity, Database, Brain, 
  Settings, Code, ToggleLeft, ToggleRight, RefreshCw, CheckCircle,
  User, Server, Clock, Globe, Terminal, Plus, Trash2
} from 'lucide-react';

// --- COMPONENTS ---

const Toggle = ({ checked, onChange }) => (
  <button 
    onClick={() => onChange(!checked)}
    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 ${checked ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`}
  >
    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
  </button>
);

const NumberInput = ({ value, onChange, label, step = 1, min }) => (
  <div className="flex flex-col gap-1">
    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>
    <input 
      type="number" 
      step={step}
      min={min}
      value={value} 
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="bg-gray-50 dark:bg-[#2a2a2a] border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 outline-none"
    />
  </div>
);

const TextInput = ({ value, onChange, label, placeholder }) => (
  <div className="flex flex-col gap-1 w-full">
    {label && <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>}
    <input 
      type="text" 
      value={value} 
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-gray-50 dark:bg-[#2a2a2a] border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 outline-none"
    />
  </div>
);

const Select = ({ value, onChange, options, label }) => (
  <div className="flex flex-col gap-1">
    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>
    <select 
      value={value} 
      onChange={(e) => onChange(e.target.value)}
      className="bg-gray-50 dark:bg-[#2a2a2a] border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 outline-none"
    >
      {options.map(opt => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  </div>
);

const TextArea = ({ value, onChange, label, rows = 4 }) => (
  <div className="flex flex-col gap-1 w-full h-full">
    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>
    <textarea 
      value={value} 
      onChange={(e) => onChange(e.target.value)}
      rows={rows}
      className="flex-1 w-full bg-gray-50 dark:bg-[#2a2a2a] border border-gray-200 dark:border-gray-700 rounded px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 outline-none resize-none font-mono leading-relaxed"
    />
  </div>
);

const DictEditor = ({ value, onChange, label }) => {
  const [entries, setEntries] = useState(Object.entries(value || {}));

  const update = (newEntries) => {
    setEntries(newEntries);
    onChange(Object.fromEntries(newEntries));
  };

  const add = () => update([...entries, ["New Group", ""]]);
  const remove = (idx) => update(entries.filter((_, i) => i !== idx));
  const changeKey = (idx, k) => {
    const next = [...entries];
    next[idx][0] = k;
    update(next);
  };
  const changeVal = (idx, v) => {
    const next = [...entries];
    next[idx][1] = v;
    update(next);
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide flex justify-between">
        {label}
        <button onClick={add} className="text-green-500 hover:text-green-600"><Plus size={14} /></button>
      </label>
      <div className="flex flex-col gap-2">
        {entries.map(([k, v], i) => (
          <div key={i} className="flex gap-2">
            <TextInput value={k} onChange={(val) => changeKey(i, val)} placeholder="Name" />
            <TextInput value={v} onChange={(val) => changeVal(i, val)} placeholder="ID" />
            <button onClick={() => remove(i)} className="text-red-500 hover:text-red-600 p-2"><Trash2 size={14} /></button>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- TABS ---

const ConfigSection = ({ title, icon: Icon, children, className = "" }) => (
  <div className={`card bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-[#363636] rounded-xl shadow-sm overflow-hidden flex flex-col ${className}`}>
    <div className="bg-gray-50 dark:bg-[#252526] px-5 py-3 border-b border-gray-200 dark:border-[#363636] flex items-center gap-2">
      <Icon size={16} className="text-gray-600 dark:text-gray-400" />
      <h3 className="text-sm font-bold text-gray-800 dark:text-gray-200 uppercase tracking-wider">{title}</h3>
    </div>
    <div className="p-5 flex flex-col gap-4 flex-1">
      {children}
    </div>
  </div>
);

const GeneralConfigTab = ({ data, setData }) => {
  if (!data || !data.identity) return <div className="p-10 text-center text-gray-500">Loading Configuration...</div>;

  const update = (section, field, value) => {
    const next = { ...data };
    if (!next[section]) next[section] = {};
    next[section][field] = value;
    setData(next);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-10">
      
      {/* IDENTITY */}
      <ConfigSection title="Identity & Personality" icon={User} className="xl:col-span-2">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
           <div className="flex flex-col gap-4">
              <TextInput label="Bot Name" value={data.identity?.BOT_NAME || ""} onChange={(v) => update('identity', 'BOT_NAME', v)} />
              <TextInput label="Bot Handle" value={data.identity?.BOT_HANDLE || ""} onChange={(v) => update('identity', 'BOT_HANDLE', v)} />
              <TextInput label="Admin Handle" value={data.identity?.ADMIN_USERNAME || ""} onChange={(v) => update('identity', 'ADMIN_USERNAME', v)} />
              <TextInput label="Triggers (comma-sep)" value={(data.identity?.TRIGGERS || []).join(', ')} onChange={(v) => update('identity', 'TRIGGERS', v.split(',').map(s=>s.trim()))} />
           </div>
           <div className="md:col-span-2 h-full">
              <TextArea label="System Profile (Persona)" value={data.identity?.PROFILE || ""} onChange={(v) => update('identity', 'PROFILE', v)} rows={12} />
           </div>
        </div>
      </ConfigSection>

      {/* MODEL */}
      <ConfigSection title="LLM Configuration" icon={Brain}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Use In-Process LLM (Llama.cpp)</span>
          <Toggle checked={data.model?.USE_IN_PROCESS_LLM || false} onChange={(v) => update('model', 'USE_IN_PROCESS_LLM', v)} />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
           {data.model?.USE_IN_PROCESS_LLM ? (
             <div className="col-span-2"><TextInput label="Model Path (.gguf)" value={data.model?.MODEL_PATH || ""} onChange={(v) => update('model', 'MODEL_PATH', v)} /></div>
           ) : (
             <div className="col-span-2"><TextInput label="Remote API URL" value={data.model?.REMOTE_LLM_URL || ""} onChange={(v) => update('model', 'REMOTE_LLM_URL', v)} /></div>
           )}
           <NumberInput label="Context Window" value={data.model?.CONTEXT_WINDOW || 4096} onChange={(v) => update('model', 'CONTEXT_WINDOW', v)} />
           <NumberInput label="Max Output Tokens" value={data.model?.MAX_TOKENS || 300} onChange={(v) => update('model', 'MAX_TOKENS', v)} />
           <NumberInput label="Temperature" step={0.1} value={data.model?.TEMPERATURE || 0.7} onChange={(v) => update('model', 'TEMPERATURE', v)} />
           <NumberInput label="GPU Layers (-1 = All)" value={data.model?.GPU_LAYERS || -1} onChange={(v) => update('model', 'GPU_LAYERS', v)} />
        </div>
      </ConfigSection>

      {/* BEHAVIOR & TIMEOUTS */}
      <div className="flex flex-col gap-6">
        <ConfigSection title="Behavior" icon={Activity}>
           <div className="grid grid-cols-3 gap-4">
              <NumberInput label="Chaos Rate" step={0.01} value={data.behavior?.BASE_CHAOS_RATE || 0.05} onChange={(v) => update('behavior', 'BASE_CHAOS_RATE', v)} />
              <NumberInput label="Reply Momentum" step={0.05} value={data.behavior?.CONTINUATION_RATE || 0.2} onChange={(v) => update('behavior', 'CONTINUATION_RATE', v)} />
              <NumberInput label="History Char Limit" value={data.behavior?.HISTORY_CHAR_LIMIT || 6000} onChange={(v) => update('behavior', 'HISTORY_CHAR_LIMIT', v)} />
           </div>
        </ConfigSection>

        <ConfigSection title="Timeouts & Delays" icon={Clock}>
           <div className="grid grid-cols-2 gap-4">
              <NumberInput label="Typing Speed (Min)" step={0.01} value={data.timeouts?.TYPING_DELAY_MIN || 0.01} onChange={(v) => update('timeouts', 'TYPING_DELAY_MIN', v)} />
              <NumberInput label="Typing Speed (Max)" step={0.01} value={data.timeouts?.TYPING_DELAY_MAX || 0.05} onChange={(v) => update('timeouts', 'TYPING_DELAY_MAX', v)} />
              <NumberInput label="Reply Delay (Min)" step={0.1} value={data.timeouts?.REPLY_DELAY_MIN || 1.5} onChange={(v) => update('timeouts', 'REPLY_DELAY_MIN', v)} />
              <NumberInput label="Reply Delay (Max)" step={0.1} value={data.timeouts?.REPLY_DELAY_MAX || 3.0} onChange={(v) => update('timeouts', 'REPLY_DELAY_MAX', v)} />
           </div>
        </ConfigSection>
      </div>

      {/* INSTAGRAM */}
      <ConfigSection title="Instagram Connection" icon={Globe} className="xl:col-span-2">
         <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col gap-4">
               <TextInput label="Direct Inbox Link" value={data.instagram?.DIRECT_LINK || ""} onChange={(v) => update('instagram', 'DIRECT_LINK', v)} />
               <TextInput label="User Agent" value={data.instagram?.USER_AGENT || ""} onChange={(v) => update('instagram', 'USER_AGENT', v)} />
               <div className="flex items-center gap-4 mt-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Headless Mode</span>
                    <Toggle checked={data.instagram?.HEADLESS || false} onChange={(v) => update('instagram', 'HEADLESS', v)} />
                  </div>
                  <div className="flex-1">
                     <NumberInput label="Browser Slow-Mo (ms)" value={data.instagram?.BROWSER_SLOW_MO || 50} onChange={(v) => update('instagram', 'BROWSER_SLOW_MO', v)} />
                  </div>
               </div>
            </div>
            <div>
               <DictEditor label="Known Groups" value={data.instagram?.GROUPS || {}} onChange={(v) => update('instagram', 'GROUPS', v)} />
            </div>
         </div>
      </ConfigSection>

    </div>
  );
};

const PluginCard = ({ name, enabled, backend, settings, onUpdate }) => {
  const getIcon = (n) => {
    switch(n) {
      case 'Dreamer': return <Brain size={18} className="text-purple-500" />;
      case 'Mimic': return <Activity size={18} className="text-blue-500" />;
      case 'Profiler': return <Database size={18} className="text-orange-500" />;
      case 'Archivist': return <Save size={18} className="text-green-500" />;
      default: return <Zap size={18} />;
    }
  };

  const handleSettingChange = (key, val) => {
    const newSettings = { ...settings, [key]: val };
    onUpdate('settings', newSettings);
  };

  return (
    <div className={`border rounded-xl p-5 transition-all ${enabled ? 'bg-white dark:bg-[#1e1e1e] border-gray-200 dark:border-gray-800 shadow-sm' : 'bg-gray-50 dark:bg-[#181818] border-gray-200 dark:border-gray-800 opacity-70'}`}>
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-100 dark:bg-[#2a2a2a] rounded-lg">
            {getIcon(name)}
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-white">{name}</h3>
            <span className="text-xs text-gray-500 dark:text-gray-400 font-mono">{enabled ? 'Active' : 'Disabled'}</span>
          </div>
        </div>
        <Toggle checked={enabled} onChange={(val) => onUpdate('enabled', val)} />
      </div>

      {enabled && (
        <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="p-3 bg-gray-50 dark:bg-[#252526] rounded-lg border border-gray-100 dark:border-[#333]">
            <Select 
              label="Backend Model" 
              value={backend} 
              options={['gemini', 'local']} 
              onChange={(val) => onUpdate('backend', val)} 
            />
          </div>
          
          <div className="grid grid-cols-2 gap-3">
             {Object.entries(settings).map(([key, val]) => {
                if (key === 'trigger_commands' || key === 'ignored_senders') {
                   return (
                     <div key={key} className="col-span-2">
                       <TextInput 
                          label={key.replace('_', ' ')}
                          value={Array.isArray(val) ? val.join(', ') : val}
                          onChange={(v) => handleSettingChange(key, v.split(',').map(s => s.trim()))}
                       />
                     </div>
                   );
                }
                if (typeof val === 'number') {
                   return (
                     <NumberInput 
                       key={key} 
                       label={key.replace('_', ' ')} 
                       value={val} 
                       onChange={(v) => handleSettingChange(key, v)} 
                       step={Number.isInteger(val) ? 1 : 0.1}
                     />
                   );
                }
                return null;
             })}
          </div>
        </div>
      )}
    </div>
  );
};

const PluginsTab = ({ data, setData }) => {
  if (!data) return <div className="p-10 text-center text-gray-500">Loading Configuration...</div>;

  const updatePlugin = (name, field, value) => {
    const newData = { ...data };
    if (field === 'enabled') newData.enabled[name] = value;
    if (field === 'backend') newData.backends[name] = value;
    if (field === 'settings') newData.settings[name] = value;
    setData(newData);
  };

  const updateGlobal = (field, value) => {
     const newData = { ...data, global: { ...data.global, [field]: value } };
     setData(newData);
  };

  return (
    <div className="flex flex-col gap-6 pb-10">
      {/* Global Settings */}
      <div className="card p-5 bg-white dark:bg-[#1e1e1e] border border-gray-200 dark:border-[#363636] rounded-xl shadow-sm">
         <h3 className="font-bold text-gray-800 dark:text-gray-200 mb-4 flex items-center gap-2">
            <Settings size={16} /> Global Plugin Settings
         </h3>
         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Select 
               label="Default Backend" 
               value={data.global.default_backend} 
               onChange={(v) => updateGlobal('default_backend', v)}
               options={['gemini', 'local']}
            />
            <TextInput 
               label="Gemini Model" 
               value={data.global.gemini_model} 
               onChange={(v) => updateGlobal('gemini_model', v)}
            />
            <div className="flex items-center gap-3 pt-6">
               <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Debug Mode</span>
               <Toggle checked={data.global.debug} onChange={(v) => updateGlobal('debug', v)} />
            </div>
         </div>
      </div>

      {/* Plugin Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
         {Object.keys(data.enabled).map(name => (
            <PluginCard 
               key={name}
               name={name}
               enabled={data.enabled[name]}
               backend={data.backends[name] || data.global.default_backend}
               settings={data.settings[name] || {}}
               onUpdate={(f, v) => updatePlugin(name, f, v)}
            />
         ))}
      </div>
    </div>
  );
};

// --- MAIN PAGE ---

export default function Config() {
  const [activeTab, setActiveTab] = useState('general');
  const [generalConfig, setGeneralConfig] = useState(null);
  const [pluginConfig, setPluginConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    const gConf = await api.get('/config/json');
    if (gConf) setGeneralConfig(gConf);
    
    const pConf = await api.get('/config/plugins/json');
    if (pConf) setPluginConfig(pConf);
    setLoading(false);
  };

  const save = async () => {
    if(!confirm("Restart system to apply changes?")) return;
    setLoading(true);
    
    // Save General
    if (generalConfig) {
       await api.post('/config/json', generalConfig);
    }
    
    // Save Plugins
    if (pluginConfig) {
       await api.post('/config/plugins/json', pluginConfig);
    }

    await api.post('/restart', {});
    setLoading(false);
    window.location.reload();
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col gap-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-4 p-1 bg-gray-100 dark:bg-[#252526] rounded-lg">
           <button 
             onClick={() => setActiveTab('general')}
             className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'general' ? 'bg-white dark:bg-[#333] shadow-sm text-green-600 dark:text-green-400' : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}`}
           >
             <Settings size={16} /> General
           </button>
           <button 
             onClick={() => setActiveTab('plugins')}
             className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'plugins' ? 'bg-white dark:bg-[#333] shadow-sm text-purple-600 dark:text-purple-400' : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}`}
           >
             <Cpu size={16} /> Plugins
           </button>
        </div>

        <button onClick={save} disabled={loading} className="btn-primary flex items-center gap-2 shadow-lg hover:shadow-green-500/20">
            {loading ? <RefreshCw size={18} className="animate-spin" /> : <Save size={18} />}
            <span>Save & Restart System</span>
        </button>
      </div>

      {/* Warnings */}
      <div className="bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-200 dark:border-yellow-900/30 rounded-lg p-3 flex items-center gap-3">
         <AlertTriangle className="text-yellow-600 dark:text-yellow-500 shrink-0" size={18} />
         <p className="text-sm text-yellow-700 dark:text-yellow-500/90 font-medium">
            Changes require a full system restart.
         </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-2 pb-20 custom-scrollbar">
         {activeTab === 'general' ? (
            <GeneralConfigTab data={generalConfig} setData={setGeneralConfig} />
         ) : (
            <PluginsTab data={pluginConfig} setData={setPluginConfig} />
         )}
      </div>
    </div>
  );
}
