import React, { useState } from 'react';

function PromptTable({ data }) {
  const [filter, setFilter] = useState('all'); // all | mentioned | missed

  if (!data || data.length === 0) {
    return (
      <div className="card">
        <h2>Query Intelligence</h2>
        <p style={{ color: '#888' }}>No data yet — run the pipeline first</p>
      </div>
    );
  }

  const filtered = data.filter((row) => {
    if (filter === 'mentioned') return row.brand_mentioned;
    if (filter === 'missed') return !row.brand_mentioned;
    return true;
  });

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ marginBottom: 0 }}>Query Intelligence ({filtered.length})</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={filter === 'all' ? 'btn btn-secondary' : 'btn btn-outline'}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          <button
            className={filter === 'mentioned' ? 'btn btn-secondary' : 'btn btn-outline'}
            onClick={() => setFilter('mentioned')}
          >
            Mentioned
          </button>
          <button
            className={filter === 'missed' ? 'btn btn-secondary' : 'btn btn-outline'}
            onClick={() => setFilter('missed')}
          >
            Missed
          </button>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Prompt</th>
            <th>Engine</th>
            <th>Geo</th>
            <th>Intent</th>
            <th>Type</th>
            <th>Result</th>
            <th>Sentiment</th>
            <th>Competitors</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((row, i) => (
            <tr key={i}>
              <td style={{ maxWidth: 320 }}>{row.prompt_text}</td>
              <td style={{ textTransform: 'capitalize' }}>{row.engine}</td>
              <td>{row.geo}</td>
              <td>{row.intent_cluster}</td>
              <td>{row.prompt_type}</td>
              <td>
                <span className={`status ${row.brand_mentioned ? 'status-complete' : 'status-failed'}`}>
                  {row.brand_mentioned ? 'Mentioned' : 'Missing'}
                </span>
              </td>
              <td>{row.sentiment}</td>
              <td style={{ color: '#888', fontSize: 12 }}>
                {row.competing_brands.join(', ') || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PromptTable;