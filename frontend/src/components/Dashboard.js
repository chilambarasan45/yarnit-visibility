import React, { useState } from 'react';
import axios from 'axios';
import Overview from './Overview';
import GeoBreakdown from './GeoBreakdown';
import EngineBreakdown from './EngineBreakdown';
import Competitors from './Competitors';
import PromptSelector from './PromptSelector';
import PipelineFlow from './PipelineFlow';
import RunHistory from './RunHistory';
import TrendChart from './TrendChart';
const API = 'http://127.0.0.1:8000/api';

function Dashboard({ brand, onBack }) {
  const [activeTab, setActiveTab]   = useState('pipeline');
  const [running, setRunning]       = useState(false);
  const [, setRunResult]   = useState(null);
  const [runMessage, setRunMessage] = useState('');

  const triggerPipeline = async () => {
    setRunning(true);
    setRunMessage('🔄 Pipeline running... this may take several minutes.');
    try {
      const res = await axios.post(`${API}/pipeline/run`, {
        brand_id: brand.id,
      });
      setRunResult(res.data);
      setRunMessage(`✅ Pipeline complete! ${res.data.success_count} responses collected.`);
    } catch (e) {
      setRunMessage('❌ Pipeline failed. Check terminal for details.');
    }
    setRunning(false);
  };

  const tabs = [
    { id: 'overview',  label: '📊 Overview'  },
    { id: 'geo',       label: '🌍 By Country' },
    { id: 'engine',    label: '🤖 By Engine'  },
    { id: 'competitors', label: '⚔️ Competitors' },
     { id: 'prompts',    label: '🎯 Test Prompts'   },
      { id: 'pipeline',    label: '⚡ Run Pipeline'  },
      { id: 'history',     label: '📋 Run History'   },
      { id: 'trend',       label: '📈 Trend'         }, 
  ];

  return (
    <div>
      {/* Back + Header */}
      <div className="back-btn">
        <button className="btn btn-outline" onClick={onBack}>
          ← Back to brands
        </button>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 22, marginBottom: 4 }}>{brand.name}</h2>
            <p style={{ color: '#888', fontSize: 14 }}>{brand.domain}</p>
          </div>
          <button
            className="btn btn-primary"
            onClick={triggerPipeline}
            disabled={running}
          >
            {running ? '⏳ Running...' : '🚀 Run Pipeline'}
          </button>
        </div>

        {runMessage && (
          <div style={{
            marginTop: 16,
            padding: '10px 16px',
            background: '#f0f7ff',
            borderRadius: 8,
            fontSize: 14,
          }}>
            {runMessage}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview'     && <Overview     brandId={brand.id} />}
      {activeTab === 'geo'          && <GeoBreakdown brandId={brand.id} />}
      {activeTab === 'engine'       && <EngineBreakdown brandId={brand.id} />}
      {activeTab === 'competitors'  && <Competitors  brandId={brand.id} />}
      {activeTab === 'prompts' && <PromptSelector brandId={brand.id} />}
      {activeTab === 'pipeline' && (<PipelineFlow brand={brand} />)}
      {activeTab === 'history' && <RunHistory brandId={brand.id} />}
      {activeTab === 'trend' && <TrendChart brandId={brand.id} />}
    </div>
  );
}

export default Dashboard;