import React, { useState } from 'react';

function GapMap({ data }) {
  const [expanded, setExpanded] = useState(null);

  if (!data || !data.competitors || data.competitors.length === 0) {
    return (
      <div className="card">
        <h2>Competitive Gap Map</h2>
        <p style={{ color: '#888' }}>No missed queries yet — run the pipeline first.</p>
      </div>
    );
  }

  const toggle = (name) => {
    setExpanded(expanded === name ? null : name);
  };

  return (
    <div className="card">
      <h2>Competitive Gap Map</h2>
      <p style={{ color: '#888', fontSize: 13, marginBottom: 16 }}>
        {data.total_missed_queries} queries where your brand wasn't mentioned —
        here's who's winning them instead.
      </p>

      {data.competitors.map((comp) => (
        <div key={comp.competitor} style={{ marginBottom: 8, borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
          <div
            onClick={() => toggle(comp.competitor)}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              cursor: 'pointer',
              padding: '8px 0',
            }}
          >
            <strong>{comp.competitor}</strong>
            <span className="status status-running">{comp.wins} {comp.wins === 1 ? 'win' : 'wins'}</span>
          </div>

          {expanded === comp.competitor && (
            <table style={{ marginTop: 8 }}>
              <thead>
                <tr>
                  <th>Prompt</th>
                  <th>Engine</th>
                  <th>Geo</th>
                  <th>Intent</th>
                </tr>
              </thead>
              <tbody>
                {comp.prompts.map((p, i) => (
                  <tr key={i}>
                    <td style={{ maxWidth: 320 }}>{p.prompt_text}</td>
                    <td style={{ textTransform: 'capitalize' }}>{p.engine}</td>
                    <td>{p.geo}</td>
                    <td>{p.intent_cluster}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </div>
  );
}

export default GapMap;