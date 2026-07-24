import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = 'http://127.0.0.1:8000/api';

function ExecutiveSummary({ brandId }) {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSummary();
  }, [brandId]);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/dashboard/${brandId}/summary`);
      setSummary(res.data.summary);
    } catch (e) {
      setSummary('Could not load summary — check terminal for details.');
    }
    setLoading(false);
  };

  return (
    <div className="card" style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      color: 'white',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ color: 'white', margin: 0 }}>🧠 Executive Summary</h2>
        <button
          className="btn btn-outline"
          onClick={fetchSummary}
          disabled={loading}
          style={{ borderColor: 'rgba(255,255,255,0.3)', color: 'white', fontSize: 12, padding: '6px 14px' }}
        >
          {loading ? '⏳' : '🔄 Refresh'}
        </button>
      </div>
      <p style={{ fontSize: 15, lineHeight: 1.6, color: 'rgba(255,255,255,0.9)', margin: 0 }}>
        {loading ? 'Generating summary...' : summary}
      </p>
    </div>
  );
}

export default ExecutiveSummary;