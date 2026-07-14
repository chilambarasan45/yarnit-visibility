

import React, { useState } from 'react';
import BrandSetup from './components/BrandSetup';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [selectedBrand, setSelectedBrand] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 Yarnit AI Visibility Platform</h1>
        <p>Track your brand across AI engines — Gemini · Perplexity</p>
      </header>

      <main className="app-main">
        {!selectedBrand ? (
          <BrandSetup onBrandSelected={setSelectedBrand} />
        ) : (
          <Dashboard
            brand={selectedBrand}
            onBack={() => setSelectedBrand(null)}
          />
        )}
      </main>
    </div>
  );
}

export default App;