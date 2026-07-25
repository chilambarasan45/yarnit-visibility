import React, { useState, useEffect } from 'react';
import api from '../api';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, Legend
} from 'recharts';
function TrendChart({ brandId }) {
    const [data, setData]       = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get(`/dashboard/${brandId}/trend`)
            .then(res => { setData(res.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, [brandId]);

    if (loading) return <div className="loading">Loading trend data...</div>;

    if (!data || data.length === 0) return (
        <div className="card">
            <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
                No trend data yet — run the pipeline at least once to start tracking.
            </p>
        </div>
    );

    // Calculate month over month change
    const latest   = data[data.length - 1];
    const previous = data.length > 1 ? data[data.length - 2] : null;
    const change   = previous
        ? (latest.visibility_score - previous.visibility_score).toFixed(1)
        : null;

    return (
        <div>
            {/* Summary cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value">
                        {latest.visibility_score}%
                    </div>
                    <div className="stat-label">Current Visibility Score</div>
                </div>

                {change !== null && (
                    <div className="stat-card">
                        <div className="stat-value" style={{
                            color: change >= 0 ? '#2e7d32' : '#c62828'
                        }}>
                            {change >= 0 ? '▲' : '▼'} {Math.abs(change)}%
                        </div>
                        <div className="stat-label">vs Last Month</div>
                    </div>
                )}

                <div className="stat-card">
                    <div className="stat-value">{data.length}</div>
                    <div className="stat-label">Months Tracked</div>
                </div>

                <div className="stat-card">
                    <div className="stat-value">
                        {data.reduce((sum, d) => sum + d.total_responses, 0)}
                    </div>
                    <div className="stat-label">Total Responses</div>
                </div>
            </div>

            {/* Line chart */}
            <div className="card">
                <h2>📈 Visibility Score Over Time</h2>
                <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>
                    How often your brand is mentioned by AI engines — month by month
                </p>
                <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" />
                        <YAxis
                            domain={[0, 100]}
                            unit="%"
                        />
                        <Tooltip
                            formatter={(value, name) => [
                                `${value}%`,
                                name === 'visibility_score' ? 'Visibility Score' : name
                            ]}
                        />
                        <Legend
                            formatter={(value) =>
                                value === 'visibility_score' ? 'Visibility Score' : value
                            }
                        />
                        <ReferenceLine
                            y={50}
                            stroke="#888"
                            strokeDasharray="4 4"
                            label={{ value: "50% target", position: "right", fontSize: 11 }}
                        />
                        <Line
                            type="monotone"
                            dataKey="visibility_score"
                            stroke="#e94560"
                            strokeWidth={3}
                            dot={{ fill: '#e94560', r: 5 }}
                            activeDot={{ r: 7 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Monthly breakdown table */}
            <div className="card">
                <h2>Monthly Breakdown</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Month</th>
                            <th>Visibility Score</th>
                            <th>Mentioned</th>
                            <th>Total Responses</th>
                            <th>Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, i) => {
                            const prev   = i > 0 ? data[i - 1] : null;
                            const diff   = prev
                                ? (row.visibility_score - prev.visibility_score).toFixed(1)
                                : null;

                            return (
                                <tr key={i}>
                                    <td>{row.month}</td>
                                    <td>
                                        <strong>{row.visibility_score}%</strong>
                                    </td>
                                    <td>{row.brand_mentioned}</td>
                                    <td>{row.total_responses}</td>
                                    <td>
                                        {diff !== null ? (
                                            <span style={{
                                                color:      diff >= 0 ? '#2e7d32' : '#c62828',
                                                fontWeight: 600,
                                            }}>
                                                {diff >= 0 ? '▲' : '▼'} {Math.abs(diff)}%
                                            </span>
                                        ) : '—'}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default TrendChart;