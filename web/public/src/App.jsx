import React, { useEffect, useState } from 'react';
import {
  Activity,
  Trophy,
  Book,
  Users,
  Zap,
  Hash,
  Camera,
  RefreshCw,
  ZoomIn
} from 'lucide-react';
import clsx from 'clsx';

// --- Shared Components matching Main Dashboard ---

const NavItem = ({ icon: Icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={clsx(
      "w-full flex items-center gap-4 px-3 py-3 rounded-lg transition-all mb-2 group text-left",
      active
        ? "text-text font-bold bg-[#262626]"
        : "text-text hover:bg-[#262626]"
    )}
  >
    <Icon size={24} className={clsx(active ? "stroke-[2.5px]" : "stroke-2")} />
    <span className={clsx("text-base", active ? "font-bold" : "font-normal")}>
      {label}
    </span>
  </button>
);

const StatCard = ({ label, children }) => (
  <div className="card p-5 relative overflow-hidden h-full flex flex-col justify-between">
    <span className="text-text-secondary text-xs font-semibold uppercase tracking-wide mb-2">{label}</span>
    {children}
  </div>
);

// --- Pages ---

const HomeView = ({ data }) => {
  const isOnline = data?.status?.is_alive && !data?.status?.is_sleeping;
  const statusColor = isOnline ? "bg-green-500" : "bg-yellow-500";
  const statusText = isOnline ? "Active" : "Sleeping";
  const msgCount = data?.status?.msg_count || 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header Hero */}
      <div className="flex items-center gap-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px]">
          <div className="w-full h-full rounded-full bg-surface p-1">
            <div className="w-full h-full rounded-full bg-gray-800 flex items-center justify-center text-xl font-bold">
              FE
            </div>
          </div>
        </div>
        <div>
          <h1 className="text-2xl font-light tracking-tight flex items-center gap-2">
            Fern Insta Bot <span className="text-blue-500 text-sm ml-1">✓</span>
          </h1>
          <div className="flex items-center gap-3 text-sm mt-1">
            <span className="font-semibold">{msgCount} <span className="font-normal text-text-secondary">messages</span></span>
            <span className="text-border">|</span>
            <div className="flex items-center gap-2">
              <div className={clsx("w-2 h-2 rounded-full", statusColor, "animate-pulse")}></div>
              <span className="font-medium text-text-secondary">{statusText}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Current Status">
          <div className="flex items-center gap-3">
            <Activity size={24} className="text-primary" />
            <span className="text-2xl font-bold">{statusText}</span>
          </div>
        </StatCard>
        <StatCard label="Residents">
          <div className="flex items-center gap-3">
            <Users size={24} className="text-purple-500" />
            <div className="flex flex-col">
              <span className="text-2xl font-bold">{data?.profiles?.length || 0}</span>
              <span className="text-xs text-text-secondary">Tracked Users</span>
            </div>
          </div>
        </StatCard>
        <StatCard label="Last Sync">
          <div className="flex items-center gap-3">
            <RefreshCw size={24} className="text-green-500" />
            <span className="text-xl font-mono">
              {new Date((data?.status?.last_updated || 0) * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </StatCard>
      </div>
    </div>
  );
};

const LeaderboardView = ({ data }) => {
  const [timeframe, setTimeframe] = useState('weekly'); // 'daily', 'weekly', 'all_time'

  const lbData = data?.leaderboard?.[timeframe] || {};
  const sorted = Object.entries(lbData)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10);

  const Tab = ({ label, id }) => (
    <button
      onClick={() => setTimeframe(id)}
      className={clsx(
        "px-4 py-2 text-sm font-semibold rounded-lg transition-colors",
        timeframe === id
          ? "bg-[#262626] text-white"
          : "text-text-secondary hover:text-text hover:bg-[#262626]/50"
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Trophy size={20} /> Leaderboard
        </h2>

        <div className="flex bg-[#121212] border border-[#363636] p-1 rounded-lg w-full sm:w-auto">
          <Tab label="Daily" id="daily" />
          <Tab label="Weekly" id="weekly" />
          <Tab label="All Time" id="all_time" />
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-[#262626] text-text-secondary text-xs uppercase hidden sm:table-header-group">
            <tr>
              <th className="p-4 font-semibold w-16 text-center">Rank</th>
              <th className="p-4 font-semibold">User</th>
              <th className="p-4 font-semibold text-right">Messages</th>
            </tr>
          </thead>
          {/* Mobile Header */}
          <thead className="bg-[#262626] text-text-secondary text-xs uppercase sm:hidden">
            <tr>
              <th className="p-3 font-semibold">User</th>
              <th className="p-3 font-semibold text-right">Msgs</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#363636]">
            {sorted.map(([handle, count], idx) => {
              // Robust lookup matching InstagramProfileModal logic
              const cleanHandle = handle.replace('@', '').toLowerCase();
              const profile = data?.profiles?.find(p =>
                p.handle.toLowerCase().replace('@', '') === cleanHandle ||
                (p.aliases && p.aliases.some(a => a.toLowerCase() === cleanHandle))
              );
              const pfpUrl = profile?.pfp_url || `https://ui-avatars.com/api/?name=${handle}&background=random`;

              return (
                <tr key={handle} className="hover:bg-[#262626]/50 transition-colors">
                  {/* Desktop Rank Column */}
                  <td className="p-4 hidden sm:table-cell">
                    <span className={clsx(
                      "font-mono font-bold w-6 h-6 flex items-center justify-center rounded-full text-xs mx-auto",
                      idx === 0 ? "bg-yellow-500 text-black" :
                        idx === 1 ? "bg-gray-400 text-black" :
                          idx === 2 ? "bg-orange-700 text-white" :
                            "text-text-secondary"
                    )}>
                      {idx + 1}
                    </span>
                  </td>

                  <td className="p-3 sm:p-4">
                    <div className="flex items-center gap-3">
                      {/* Mobile Rank Indicator (inline) */}
                      <div className={clsx(
                        "sm:hidden flex-shrink-0 font-mono font-bold w-5 h-5 flex items-center justify-center rounded-full text-[10px]",
                        idx === 0 ? "bg-yellow-500 text-black" :
                          idx === 1 ? "bg-gray-400 text-black" :
                            idx === 2 ? "bg-orange-700 text-white" :
                              "bg-[#363636] text-text-secondary"
                      )}>
                        {idx + 1}
                      </div>

                      {/* Profile Picture */}
                      <div className="relative flex-shrink-0">
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[1.5px]">
                          <div className="w-full h-full rounded-full bg-[#121212] p-0.5">
                            <img
                              src={pfpUrl}
                              alt={handle}
                              className="w-full h-full rounded-full object-cover bg-gray-800"
                              onError={(e) => e.target.src = `https://ui-avatars.com/api/?name=${handle}&background=random`}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-col">
                        <span className="font-medium text-text text-sm sm:text-base">{handle}</span>
                        {profile?.title && (
                          <span className="text-[10px] text-text-secondary uppercase tracking-wider hidden sm:block">{profile.title}</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-3 sm:p-4 text-right font-mono text-primary font-bold text-sm sm:text-base">{count}</td>
                </tr>
              )
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={3} className="p-8 text-center text-text-secondary italic">
                  No messages recorded for this period yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const LoreView = ({ data }) => {
  const lore = data?.lore || {};
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');

  // Extract all unique categories
  const allCategories = ['All', ...new Set(
    Object.values(lore)
      .flatMap(item => item.category ? item.category.split('|').map(c => c.trim()) : ['Uncategorized'])
  )].sort();

  // Filter Logic
  const filtered = Object.entries(lore).filter(([key, item]) => {
    const matchesSearch = key.toLowerCase().includes(search.toLowerCase()) ||
      item.definition.toLowerCase().includes(search.toLowerCase());
    const itemCategories = item.category ? item.category.split('|').map(c => c.trim()) : ['Uncategorized'];
    const matchesCategory = activeCategory === 'All' || itemCategories.includes(activeCategory);

    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500 min-h-[80vh]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Book size={20} /> Knowledge Base
        </h2>

        {/* Search */}
        <div className="relative w-full md:w-64">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <ZoomIn size={14} className="text-text-tertiary" />
          </div>
          <input
            type="text"
            placeholder="Search lore..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#121212] border border-[#363636] rounded-lg pl-9 pr-3 py-2 text-sm text-text focus:outline-none focus:border-primary transition-colors placeholder:text-text-tertiary"
          />
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        {allCategories.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={clsx(
              "px-3 py-1 rounded-full text-xs font-medium border transition-all",
              activeCategory === cat
                ? "bg-text text-bg border-text"
                : "bg-transparent text-text-secondary border-[#363636] hover:border-text-secondary"
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(([key, item]) => {
          const categories = item.category ? item.category.split('|').map(c => c.trim()) : [];

          return (
            <div key={key} className="card p-5 flex flex-col gap-3 group hover:border-text/30 transition-colors">
              <div className="flex items-start justify-between gap-4">
                <h3 className="font-bold text-lg text-text leading-tight">{key}</h3>
                {item.usage_count > 1 && (
                  <span className="shrink-0 text-[10px] font-mono bg-[#262626] px-1.5 py-0.5 rounded text-primary border border-[#363636]">
                    x{item.usage_count}
                  </span>
                )}
              </div>

              {/* Tags */}
              {categories.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {categories.map((cat, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-[#1c1c1c] text-text-secondary border border-[#262626]">
                      {cat}
                    </span>
                  ))}
                </div>
              )}

              <p className="text-text-secondary text-sm leading-relaxed flex-1">
                {item.definition}
              </p>

              <div className="pt-3 mt-auto border-t border-[#262626] flex items-center justify-between text-[10px] text-[#555] font-mono">
                <span>
                  {item.first_seen ? `Seen: ${new Date(item.first_seen * 1000).toLocaleDateString()}` : 'Date Unknown'}
                </span>
                {item.last_updated && (
                  <span>
                    Upd: {new Date(item.last_updated * 1000).toLocaleDateString()}
                  </span>
                )}
              </div>
            </div>
          )
        })}

        {filtered.length === 0 && (
          <div className="col-span-full py-20 flex flex-col items-center justify-center text-text-tertiary">
            <Hash size={48} className="mb-4 opacity-20" />
            <p>No lore found matching your search.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const InstagramProfileModal = ({ profile, onClose, allProfiles = [] }) => {
  if (!profile) return null;

  const stats = [
    { label: 'Messages', value: profile.message_count || 0 },
    { label: 'Traits', value: profile.traits?.length || 0 },
    { label: 'Connections', value: Object.keys(profile.relationships || {}).length || 0 },
  ];

  // Helper to find PFP of a related user
  const getRelatedPfp = (handle) => {
    // Clean handle of @ for matching
    const cleanHandle = handle.replace('@', '').toLowerCase();
    const found = allProfiles.find(p =>
      p.handle.toLowerCase().replace('@', '') === cleanHandle ||
      (p.aliases && p.aliases.some(a => a.toLowerCase() === cleanHandle))
    );
    return found?.pfp_url;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 animate-in fade-in duration-300" onClick={onClose}>
      <div className="bg-[#000] w-full max-w-[470px] h-[85vh] rounded-xl border border-[#262626] flex flex-col overflow-hidden relative shadow-2xl" onClick={e => e.stopPropagation()}>

        {/* Navbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#262626] bg-[#000] shrink-0 z-20">
          <div className="font-semibold text-sm opacity-0">Back</div>
          <div className="font-bold text-base flex items-center gap-1">
            {profile.handle}
            <span className="text-blue-500 text-[10px] ml-0.5">✓</span>
          </div>
          <button onClick={onClose} className="text-white hover:opacity-70 transition-opacity">
            <RefreshCw className="rotate-45" size={24} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto custom-scrollbar flex-1 bg-[#000]">

          {/* Header Section */}
          <div className="px-5 pt-6 pb-2">
            <div className="flex items-center gap-6 md:gap-8 mb-6">
              {/* PFP */}
              <div className="w-20 h-20 md:w-24 md:h-24 rounded-full p-[2px] bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 shrink-0">
                <div className="w-full h-full rounded-full bg-[#000] p-1">
                  <img
                    src={profile.pfp_url || `https://ui-avatars.com/api/?name=${profile.handle}&background=random`}
                    className="w-full h-full rounded-full object-cover bg-gray-900"
                  />
                </div>
              </div>

              {/* Stats */}
              <div className="flex-1 flex justify-around">
                {stats.map((stat) => (
                  <div key={stat.label} className="flex flex-col items-center">
                    <span className="font-bold text-lg leading-tight">{stat.value}</span>
                    <span className="text-sm text-text-secondary">{stat.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Bio */}
            <div className="space-y-1">
              <div className="font-bold text-sm text-[#f5f5f5]">{profile.title}</div>
              {profile.aliases && profile.aliases.length > 0 && (
                <div className="text-xs text-[#a8a8a8]">aka {profile.aliases.join(', ')}</div>
              )}
              {profile.quote && (
                <div className="text-sm text-[#f5f5f5] whitespace-pre-wrap leading-tight mt-2">
                  {profile.quote}
                </div>
              )}

              {/* Traits as Clean Pills */}
              {profile.traits && profile.traits.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {profile.traits.map((trait, i) => (
                    <span key={i} className="px-3 py-1 rounded-full bg-[#1c1c1c] border border-[#333] text-xs font-medium text-[#e0e0e0] cursor-default hover:bg-[#262626] transition-colors">
                      {trait}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Divider with Title */}
          <div className="sticky top-0 bg-[#000] z-10 py-3 border-t border-[#262626] mt-4 px-5">
            <span className="text-xs font-bold text-[#888] uppercase tracking-wider">Connections</span>
          </div>

          {/* Content: Tagged People List (Relationships) */}
          <div className="px-2 space-y-2">
            {profile.relationships && Object.keys(profile.relationships).length > 0 ? (
              <div className="flex flex-col gap-2">
                {Object.entries(profile.relationships).map(([person, desc], i) => {
                  const relativePfp = getRelatedPfp(person);
                  return (
                    <div key={i} className="flex items-start gap-3 p-3 bg-[#111] border border-[#222] rounded-xl hover:bg-[#161616] transition-colors">
                      {/* Avatar */}
                      <div className="w-10 h-10 rounded-full bg-[#262626] shrink-0 overflow-hidden border border-[#333]">
                        <img
                          src={relativePfp || `https://ui-avatars.com/api/?name=${person}&background=random`}
                          className="w-full h-full rounded-full object-cover"
                          onError={(e) => e.target.src = `https://ui-avatars.com/api/?name=${person}&background=random`}
                        />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center">
                          <span className="font-bold text-sm text-white">{person}</span>
                        </div>
                        <p className="text-xs text-[#999] mt-1 leading-relaxed">
                          {desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-10 flex flex-col items-center text-text-secondary gap-3 opacity-50">
                <span className="text-sm">No connections found.</span>
              </div>
            )}
          </div>

          {/* Divider with Title for Analysis */}
          {profile.fern_thought && (
            <>
              <div className="sticky top-0 bg-[#000] z-10 py-3 border-t border-[#262626] mt-6 px-5">
                <span className="text-xs font-bold text-[#888] uppercase tracking-wider">Fern's Analysis</span>
              </div>
              <div className="px-5 pb-6">
                <div className="bg-[#1a1a1a] rounded-lg p-4 border border-[#262626] relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 blur-3xl rounded-full -mr-16 -mt-16 pointer-events-none"></div>
                  <div className="flex items-center gap-2 mb-2 relative z-10">
                    <Zap size={14} className="text-primary fill-primary" />
                    <span className="text-xs font-bold text-primary uppercase tracking-wide">Insight</span>
                  </div>
                  <p className="text-sm text-[#dcdcdc] leading-relaxed relative z-10">
                    {profile.fern_thought}
                  </p>
                </div>
              </div>
            </>
          )}

          {/* Footer: Last Updated */}
          <div className="py-6 border-t border-[#262626] mt-4 flex justify-center">
            <span className="text-[10px] text-[#555] font-mono uppercase tracking-widest">
              Last Updated: {profile.last_updated ? new Date(profile.last_updated * 1000).toLocaleString() : 'Negotiating with Time...'}
            </span>
          </div>

        </div>
      </div>
    </div>
  );
};

const ProfilesView = ({ data }) => {
  const profiles = data?.profiles || [];
  const [selectedProfile, setSelectedProfile] = useState(null);

  // Sorting: High Message Count -> Low
  const sortedProfiles = [...profiles].sort((a, b) => {
    return (b.message_count || 0) - (a.message_count || 0);
  });

  return (
    <>
      <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Users size={20} /> Community
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedProfiles.map((p) => (
            <div
              key={p.handle}
              onClick={() => setSelectedProfile(p)}
              className="card p-6 flex flex-col items-center text-center hover:bg-[#262626] transition-all cursor-pointer group hover:border-primary/50 relative"
            >
              <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <ZoomIn size={16} className="text-text-tertiary" />
              </div>

              {/* Message Count Badge */}
              <div className="absolute top-3 left-3 bg-[#262626] border border-[#363636] px-2 py-0.5 rounded text-[10px] font-mono text-text-secondary flex items-center gap-1 group-hover:border-primary/50 group-hover:text-primary transition-colors">
                <Activity size={10} /> {p.message_count || 0}
              </div>

              <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 p-[2px] mb-4 group-hover:scale-110 transition-transform duration-300">
                <div className="w-full h-full rounded-full bg-surface p-1">
                  <img
                    src={p.pfp_url || `https://ui-avatars.com/api/?name=${p.handle}&background=random`}
                    className="w-full h-full rounded-full object-cover bg-gray-800"
                    onError={(e) => e.target.src = `https://ui-avatars.com/api/?name=${p.handle}&background=random`}
                  />
                </div>
              </div>

              <h3 className="font-bold text-lg text-text group-hover:text-white transition-colors">{p.handle}</h3>
              <p className="text-xs text-primary font-medium uppercase tracking-wider mt-1 mb-4">{p.title}</p>

              {p.quote && (
                <div className="bg-[#121212] p-3 rounded-lg w-full mt-auto">
                  <p className="text-xs text-text-secondary italic line-clamp-2">"{p.quote}"</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <InstagramProfileModal profile={selectedProfile} onClose={() => setSelectedProfile(null)} allProfiles={profiles} />
    </>
  );
}

// --- Main App ---

function App() {
  const [data, setData] = useState(null);
  const [view, setView] = useState('home');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Force Dark Mode for this view
    document.documentElement.classList.add('dark');

    fetch('/db.json')
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch db.json", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="min-h-screen bg-[#121212] flex items-center justify-center">
      <Zap className="animate-bounce text-primary" />
    </div>;
  }

  return (
    <div className="flex h-screen w-full bg-[#121212] text-[#f5f5f5] font-sans antialiased selection:bg-primary/30">

      {/* SIDEBAR (Desktop) */}
      <aside className="w-[245px] bg-[#1e1e1e] border-r border-[#363636] flex flex-col pt-8 px-3 pb-5 hidden md:flex z-10">
        <div className="px-3 mb-8">
          <div className="font-sans text-2xl font-bold italic tracking-tighter flex items-center gap-2">
            <span className="bg-clip-text text-transparent bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600">Fern</span>
            <span className="text-[#f5f5f5] not-italic font-light">Public</span>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          <NavItem icon={Activity} label="Status" active={view === 'home'} onClick={() => setView('home')} />
          <NavItem icon={Trophy} label="Leaderboard" active={view === 'leaderboard'} onClick={() => setView('leaderboard')} />
          <NavItem icon={Book} label="Lore Library" active={view === 'lore'} onClick={() => setView('lore')} />
          <NavItem icon={Users} label="Residents" active={view === 'profiles'} onClick={() => setView('profiles')} />
        </nav>

        <div className="mt-auto px-3">
          <p className="text-xs text-[#737373]">Read-Only Access • Port 8856</p>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#121212] overflow-auto">
        <div className="max-w-[1200px] w-full mx-auto p-4 md:p-8">
          {view === 'home' && <HomeView data={data} />}
          {view === 'leaderboard' && <LeaderboardView data={data} />}
          {view === 'lore' && <LoreView data={data} />}
          {view === 'profiles' && <ProfilesView data={data} />}
        </div>
      </main>

      {/* MOBILE NAV */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-[#1e1e1e] border-t border-[#363636] flex justify-around p-3 z-50">
        <button onClick={() => setView('home')} className={view === 'home' ? "text-primary" : "text-[#737373]"}><Activity size={24} /></button>
        <button onClick={() => setView('leaderboard')} className={view === 'leaderboard' ? "text-primary" : "text-[#737373]"}><Trophy size={24} /></button>
        <button onClick={() => setView('lore')} className={view === 'lore' ? "text-primary" : "text-[#737373]"}><Book size={24} /></button>
        <button onClick={() => setView('profiles')} className={view === 'profiles' ? "text-primary" : "text-[#737373]"}><Users size={24} /></button>
      </div>

    </div>
  );
}

export default App;
