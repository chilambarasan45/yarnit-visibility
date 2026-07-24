
import React, { useState, useEffect } from 'react';
import api from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const GEO_NAMES = { IN: '🇮🇳 India', AE: '🇦🇪 UAE', GB: '🇬🇧 UK' };

function GeoBreakdown({ brandId }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/dashboard/${brandId}/by-geo`)
      .then(res => { setData(res.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [brandId]);

  if (loading) return <div className="loading">Loading geo data...</div>;
  if (!data || Object.keys(data).length === 0) return (
    <div className="card">
      <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
        No geo data yet — run the pipeline first.
      </p>
    </div>
  );

  const chartData = Object.entries(data).map(([geo, values]) => ({
    name:  GEO_NAMES[geo] || geo,
    score: values.visibility_score,
    total: values.total,
  }));

  return (
    <div>
      <div className="stats-grid">
        {Object.entries(data).map(([geo, values]) => (
          <div className="stat-card" key={geo}>
            <div className="stat-value">{values.visibility_score}%</div>
            <div className="stat-label">{GEO_NAMES[geo] || geo}</div>
            <div style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
              {values.mentioned} / {values.total} responses
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Visibility Score by Country</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis domain={[0, 100]} unit="%" />
            <Tooltip formatter={(value) => `${value}%`} />
            <Bar dataKey="score" fill="#e94560" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default GeoBreakdown;