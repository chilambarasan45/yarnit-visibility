import React, { useState, useEffect } from 'react';
import api from '../api';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import axios from 'axios';
const COLORS = ['#e94560', '#1a1a2e', '#4caf50', '#ff9800', '#9c27b0'];

function Overview({ brandId }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview();
  }, [brandId]);

  const fetchOverview = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/dashboard/${brandId}/overview`);
      setData(res.data);
    } catch (e) {
      console.error('Error fetching overview:', e);
    }
    setLoading(false);
  };

  if (loading) return <div className="loading">Loading overview...</div>;
  if (!data || data.message) return (
    <div className="card">
      <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
        No data yet — click "Run Pipeline" to start tracking this brand.
      </p>
    </div>
  );

  const score     = data.visibility_score || 0;
  const scoreClass = score >= 60 ? 'score-high' : score >= 30 ? 'score-medium' : 'score-low';

  const pieData = [
    { name: 'Mentioned',     value: data.brand_mentioned },
    { name: 'Not Mentioned', value: data.total_responses - data.brand_mentioned },
  ];

  return (
    <div>
      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className={`score-badge ${scoreClass}`}>{score}%</div>
          <div className="stat-label">AI Visibility Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_responses}</div>
          <div className="stat-label">Total Responses</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.brand_mentioned}</div>
          <div className="stat-label">Times Mentioned</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.brand_cited}</div>
          <div className="stat-label">Times Cited</div>
        </div>
      </div>

      {/* Pie chart */}
      <div className="card">
        <h2>Mention Rate</h2>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              outerRadius={100}
              dataKey="value"
              label={({ name, percent }) =>
                `${name}: ${(percent * 100).toFixed(1)}%`
              }
            >
              {pieData.map((entry, index) => (
                <Cell key={index} fill={COLORS[index]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default Overview;