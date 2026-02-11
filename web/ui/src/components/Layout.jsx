import React, { useEffect, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  Home,
  TerminalSquare,
  Users,
  Settings,
  Moon,
  Sun,
  Database,
  Brain,
  Sparkles
} from 'lucide-react';
import { api, socket } from '../services/api';
import clsx from 'clsx';

const NavItem = ({ to, icon: Icon, label }) => {
  return (
    <NavLink 
      to={to} 
      className={({ isActive }) => clsx(
        "flex items-center gap-4 px-3 py-3 rounded-lg transition-all mb-2 group",
        isActive 
          ? "text-text font-bold" 
          : "text-text hover:bg-gray-100 dark:hover:bg-[#2c2c2c]"
      )}
    >
      {({ isActive }) => (
        <>
          <Icon size={24} className={clsx(isActive ? "stroke-[2.5px]" : "stroke-2")} />
          <span className={clsx("text-base", isActive ? "font-bold" : "font-normal")}>
            {label}
          </span>
        </>
      )}
    </NavLink>
  );
};

export default function Layout() {
  const [isSleeping, setIsSleeping] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    if (darkMode) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');

    socket.connect();
    
    const unsub = socket.subscribe((data) => {
      if (data.type === 'meta') {
        if (data.is_sleeping !== undefined) setIsSleeping(data.is_sleeping);
      }
    });

    api.get('/status').then(res => {
      if(res) setIsSleeping(res.is_sleeping);
    });

    return () => unsub();
  }, [darkMode]);

  const toggleSleep = async () => {
    const cmd = isSleeping ? '/wake' : '/sleep';
    await api.post('/command', { text: cmd });
    setIsSleeping(!isSleeping);
  };

  return (
    <div className="flex h-screen w-full bg-bg text-text transition-colors duration-200">
      
      {/* Sidebar Navigation */}
      <aside className="w-[245px] bg-surface border-r border-border flex flex-col pt-8 px-3 pb-5 hidden md:flex z-10">
        <div className="px-3 mb-8">
           <div className="font-sans text-2xl font-bold italic tracking-tighter flex items-center gap-2">
             <span className="bg-clip-text text-transparent bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600">Fern</span>
             <span className="text-text not-italic font-light">Nexus</span>
           </div>
        </div>

        <nav className="flex-1">
          <NavItem to="/" icon={Home} label="Home" />
          <NavItem to="/console" icon={TerminalSquare} label="Console" />
          <NavItem to="/playground" icon={Sparkles} label="Playground" />
          <NavItem to="/context" icon={Brain} label="Context" />
          <NavItem to="/memories" icon={Database} label="Memories" />
          <NavItem to="/clones" icon={Users} label="Personas" />
          <NavItem to="/config" icon={Settings} label="Settings" />
        </nav>

        <div className="mt-auto pt-4 border-t border-border space-y-2">
           <button 
             onClick={toggleSleep}
             className="w-full flex items-center gap-4 px-3 py-3 rounded-lg text-text hover:bg-gray-100 dark:hover:bg-[#2c2c2c] transition-colors text-left"
           >
             {isSleeping ? <Moon size={24} /> : <Sun size={24} />}
             <span>{isSleeping ? "Sleep Mode" : "Active Mode"}</span>
           </button>
           
           <button 
             onClick={() => setDarkMode(!darkMode)}
             className="w-full flex items-center gap-4 px-3 py-3 rounded-lg text-text-secondary hover:bg-gray-100 dark:hover:bg-[#2c2c2c] transition-colors text-left text-sm"
           >
             {darkMode ? "Switch to Light" : "Switch to Dark"}
           </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-bg transition-colors duration-200">
        <div className="flex-1 overflow-auto">
           <div className="max-w-[1200px] mx-auto w-full h-full p-0 md:p-8">
              <Outlet />
           </div>
        </div>
      </main>
      
      {/* Mobile Bottom Nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-border flex justify-around p-3 z-50">
        <NavLink to="/" className={({isActive}) => isActive ? "text-primary" : "text-text"}><Home size={24}/></NavLink>
        <NavLink to="/console" className={({isActive}) => isActive ? "text-primary" : "text-text"}><TerminalSquare size={24}/></NavLink>
        <NavLink to="/context" className={({isActive}) => isActive ? "text-primary" : "text-text"}><Brain size={24}/></NavLink>
        <NavLink to="/memories" className={({isActive}) => isActive ? "text-primary" : "text-text"}><Database size={24}/></NavLink>
        <NavLink to="/config" className={({isActive}) => isActive ? "text-primary" : "text-text"}><Settings size={24}/></NavLink>
      </div>
    </div>
  );
}