import React, { useState } from 'react';
import api from '../api';
import Overview from './Overview';
import GeoBreakdown from './GeoBreakdown';
import EngineBreakdown from './EngineBreakdown';
import Competitors from './Competitors';
import PromptSelector from './PromptSelector';
import PipelineFlow from './PipelineFlow';
import RunHistory from './RunHistory';
import TrendChart from './TrendChart';
import ExecutiveSummary from './ExecutiveSummary';

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
      { id: 'schedule',    label: '⏰ Auto-Run'      },
  ];

  return (
    <div>
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

      <ExecutiveSummary brandId={brand.id} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
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

      {activeTab === 'overview'     && <Overview     brandId={brand.id} />}
      {activeTab === 'geo'          && <GeoBreakdown brandId={brand.id} />}
      {activeTab === 'engine'       && <EngineBreakdown brandId={brand.id} />}
      {activeTab === 'competitors'  && <Competitors  brandId={brand.id} />}
      {activeTab === 'prompts' && <PromptSelector brandId={brand.id} />}
      {activeTab === 'pipeline' && (<PipelineFlow brand={brand} />)}
      {activeTab === 'history' && <RunHistory brandId={brand.id} />}
      {activeTab === 'trend' && <TrendChart brandId={brand.id} />}
      {activeTab === 'schedule' && <ScheduleSettings brandId={brand.id} />}
    </div>
  );
}

function ScheduleSettings({ brandId }) {
  const [enabled, setEnabled] = useState(false);
  const [day, setDay] = useState('monday');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  React.useEffect(() => {
    fetchStatus();
    // eslint-disable-next-line
  }, [brandId]);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/brands/${brandId}/schedule`);
      setEnabled(res.data.auto_run_enabled || false);
      setDay(res.data.auto_run_day || 'monday');
    } catch (e) {
      console.error('Error fetching schedule status:', e);
    }
    setLoading(false);
  };

  const saveSchedule = async (newEnabled, newDay) => {
    setSaving(true);
    setMessage('');
    try {
      await axios.post(`${API}/brands/${brandId}/schedule`, {
        auto_run_enabled: newEnabled,
        auto_run_day: newDay,
      });
      setMessage(newEnabled
        ? `✅ Auto-run enabled — pipeline will run every ${newDay}.`
        : '✅ Auto-run disabled.');
    } catch (e) {
      setMessage('❌ Could not save schedule. Check terminal for details.');
    }
    setSaving(false);
  };

  const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

  if (loading) return <div className="loading">Loading schedule settings...</div>;

  return (
    <div className="card">
      <h2>⏰ Automatic weekly runs</h2>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>
        When enabled, the full pipeline (crawl → BIO → prompts → fire → parse)
        runs automatically once a week, so your visibility trend stays current
        without manually clicking "Run Pipeline" each time.
      </p>

      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={e => {
              setEnabled(e.target.checked);
              saveSchedule(e.target.checked, day);
            }}
            style={{ width: 'auto' }}
          />
          <span>Enable automatic weekly run</span>
        </label>
      </div>

      {enabled && (
        <div style={{ marginBottom: 16 }}>
          <label>Run every</label>
          <select
            value={day}
            onChange={e => {
              setDay(e.target.value);
              saveSchedule(enabled, e.target.value);
            }}
            style={{ maxWidth: 200 }}
          >
            {DAYS.map(d => (
              <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
            ))}
          </select>
        </div>
      )}

      {saving && <p style={{ color: '#888', fontSize: 13 }}>Saving...</p>}
      {message && (
        <div style={{
          padding: '10px 16px',
          background: '#f0f7ff',
          borderRadius: 8,
          fontSize: 14,
        }}>
          {message}
        </div>
      )}
    </div>
  );
}

export default Dashboard;