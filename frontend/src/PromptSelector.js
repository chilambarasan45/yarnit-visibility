import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = 'http://127.0.0.1:8000/api';

function PromptSelector({ brandId, onResultsReady }) {
  const [prompts, setPrompts]         = useState([]);
  const [selected, setSelected]       = useState([]);
  const [loading, setLoading]         = useState(true);
  const [firing, setFiring]           = useState(false);
  const [results, setResults]         = useState(null);
  const [message, setMessage]         = useState('');

  useEffect(() => {
    fetchPrompts();
  }, [brandId]);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/brands/${brandId}/prompts`);
      setPrompts(res.data);
    } catch (e) {
      setMessage('❌ No prompts yet — run the pipeline first to generate prompts.');
    }
    setLoading(false);
  };

  const toggleSelect = (promptId) => {
    if (selected.includes(promptId)) {
      setSelected(selected.filter(id => id !== promptId));
    } else {
      if (selected.length >= 10) {
        setMessage('⚠️ Maximum 10 prompts can be selected at once.');
        return;
      }
      setSelected([...selected, promptId]);
    }
  };

  const fireSelected = async () => {
    if (selected.length < 1) {
      setMessage('⚠️ Please select at least 1 prompt.');
      return;
    }
    setFiring(true);
    setMessage('🔥 Firing selected prompts at Gemini...');
    try {
      const res = await axios.post(`${API}/pipeline/fire-selected`, {
        brand_id:   brandId,
        prompt_ids: selected,
      });
      setResults(res.data.results);
      setMessage(`✅ Done! ${res.data.total} prompts fired.`);
      if (onResultsReady) onResultsReady(res.data.results);
    } catch (e) {
      setMessage('❌ Error firing prompts. Check terminal for details.');
    }
    setFiring(false);
  };

  if (loading) return <div className="loading">Loading prompts...</div>;

  return (
    <div>
      {/* Instructions */}
      <div className="card">
        <h2>🎯 Select Prompts to Test</h2>
        <p style={{ color: '#888', fontSize: 14, marginBottom: 16 }}>
          Select 5–10 prompts from the list below. Only selected prompts
          will be fired at Gemini to check for brand mentions and citations.
        </p>

        {message && (
          <div style={{
            padding: '10px 16px',
            background: '#f0f7ff',
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 14,
          }}>
            {message}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: '#888' }}>
            {selected.length} / 10 selected
          </span>
          <button
            className="btn btn-primary"
            onClick={fireSelected}
            disabled={firing || selected.length === 0}
          >
            {firing ? '⏳ Firing...' : `🚀 Fire ${selected.length} Selected Prompts`}
          </button>
        </div>
      </div>

      {/* Prompt list */}
      {prompts.length === 0 ? (
        <div className="card">
          <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
            No prompts generated yet. Run the pipeline first.
          </p>
        </div>
      ) : (
        <div className="card">
          <h2>Generated Prompts ({prompts.length} total)</h2>
          <table>
            <thead>
              <tr>
                <th>Select</th>
                <th>Prompt</th>
                <th>Intent</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {prompts.map(p => (
                <tr
                  key={p.id}
                  onClick={() => toggleSelect(p.id)}
                  style={{
                    cursor: 'pointer',
                    background: selected.includes(p.id) ? '#fff3e0' : 'white',
                  }}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.includes(p.id)}
                      onChange={() => toggleSelect(p.id)}
                      style={{ width: 'auto' }}
                    />
                  </td>
                  <td>{p.prompt_text}</td>
                  <td>
                    <span className="status status-complete">
                      {p.intent_cluster}
                    </span>
                  </td>
                  <td>{p.prompt_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="card">
          <h2>📊 Results</h2>
          <table>
            <thead>
              <tr>
                <th>Prompt</th>
                <th>Mentioned?</th>
                <th>Cited?</th>
                <th>Mention Form</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: 300 }}>{r.prompt_text}</td>
                  <td>
                    <span className={`status ${r.brand_mentioned ? 'status-complete' : 'status-failed'}`}>
                      {r.brand_mentioned ? '✅ Yes' : '❌ No'}
                    </span>
                  </td>
                  <td>
                    <span className={`status ${r.brand_cited ? 'status-complete' : 'status-failed'}`}>
                      {r.brand_cited ? '✅ Yes' : '❌ No'}
                    </span>
                  </td>
                  <td>{r.mention_form}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PromptSelector;