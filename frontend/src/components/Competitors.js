import React, { useState, useEffect } from 'react';
import api from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../api';

function Competitors({ brandId }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/dashboard/${brandId}/overview`)
      .then(res => { setData(res.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [brandId]);

  if (loading) return <div className="loading">Loading competitor data...</div>;
  if (!data || !data.top_competitors || data.top_competitors.length === 0) return (
    <div className="card">
      <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
        No competitor data yet — run the pipeline first.
      </p>
    </div>
  );

  const chartData = data.top_competitors.slice(0, 8).map(c => ({
    name:     c.brand,
    mentions: c.mentions,
  }));

  return (
    <div>
      <div className="card">
        <h2>⚔️ Top Competing Brands</h2>
        <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>
          These brands appeared in AI responses instead of or alongside {data.brand_name}
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis type="category" dataKey="name" width={120} />
            <Tooltip />
            <Bar dataKey="mentions" fill="#e94560" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2>Full Competitor List</h2>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Brand</th>
              <th>AI Mentions</th>
            </tr>
          </thead>
          <tbody>
            {data.top_competitors.map((c, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{c.brand}</td>
                <td>{c.mentions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Competitors;