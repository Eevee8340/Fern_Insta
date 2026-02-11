import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Console from './pages/Console';
import Context from './pages/Context';
import Memories from './pages/Memories';
import Clones from './pages/Clones';
import Config from './pages/Config';
import Playground from './pages/Playground';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="console" element={<Console />} />
          <Route path="playground" element={<Playground />} />
          <Route path="context" element={<Context />} />
          <Route path="memories" element={<Memories />} />
          <Route path="clones" element={<Clones />} />
          <Route path="config" element={<Config />} />
          
          {/* Legacy Redirects */}
          <Route path="chat" element={<Console />} />
          <Route path="terminal" element={<Console />} />
          
          <Route path="*" element={<div className="p-10 text-center text-text-secondary font-mono">404 // MODULE NOT FOUND</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;