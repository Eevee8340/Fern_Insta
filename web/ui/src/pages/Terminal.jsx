import React, { useEffect, useState, useRef } from 'react';
import { socket, api } from '../services/api';
import clsx from 'clsx';
import { Terminal as TerminalIcon } from 'lucide-react';

export default function Terminal() {
  const [logs, setLogs] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    api.get('/logs').then(res => {
      if (res && res.logs) setLogs(res.logs.map((l, i) => ({ text: l, id: i })));
    });

    const unsub = socket.subscribe((data) => {
      if (data.type === 'log') {
        setLogs(prev => [...prev.slice(-199), { text: data.text, id: Date.now() }]);
      }
    });

    return () => unsub();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="card h-[calc(100vh-140px)] flex flex-col overflow-hidden bg-[#1e1e1e] border-none shadow-xl">
      <div className="px-4 py-3 bg-[#252526] border-b border-[#333] flex items-center gap-2">
        <TerminalIcon size={14} className="text-blue-400" />
        <span className="text-xs font-mono text-gray-300">OUTPUT</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-5 text-gray-300">
        {logs.map((log, i) => (
          <div key={log.id || i} className="whitespace-pre-wrap break-all border-l-2 border-transparent hover:bg-white/5 pl-2 transition-colors">
             <span className="text-gray-500 mr-3 select-none">{new Date().toLocaleTimeString()}</span>
             {log.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}