import React, { useState, useEffect } from 'react';
import api from '../api';


function RunHistory({ brandId }) {
  const [runs, setRuns]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns();
  }, [brandId]);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/pipeline/runs/${brandId}`);
      setRuns(res.data);
    } catch (e) {
      console.error('Error fetching runs:', e);
    }
    setLoading(false);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString();
  };

  const getDuration = (start, end) => {
    if (!start || !end) return '—';
    const diff = new Date(end) - new Date(start);
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  if (loading) return <div className="loading">Loading run history...</div>;

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2>📋 Run History</h2>
          <button className="btn btn-outline" onClick={fetchRuns}>
            🔄 Refresh
          </button>
        </div>

        {runs.length === 0 ? (
          <p style={{ color: '#888', textAlign: 'center', padding: 40 }}>
            No runs yet — use the Pipeline tab to start your first run.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
                <th>Total Calls</th>
                <th>Success</th>
                <th>Failed</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr key={run.id}>
                  <td style={{ color: '#888', fontSize: 12 }}>
                    {runs.length - i}
                  </td>
                  <td>
                    <span className={`status status-${run.status}`}>
                      {run.status === 'complete'  && '✅ Complete'}
                      {run.status === 'running'   && '⏳ Running'}
                      {run.status === 'failed'    && '❌ Failed'}
                      {run.status === 'queued'    && '🕐 Queued'}
                    </span>
                  </td>
                  <td style={{ fontSize: 13 }}>{formatDate(run.started_at)}</td>
                  <td style={{ fontSize: 13 }}>{getDuration(run.started_at, run.completed_at)}</td>
                  <td style={{ textAlign: 'center' }}>{run.total_calls || 0}</td>
                  <td style={{ textAlign: 'center', color: '#2e7d32' }}>
                    {run.success_count || 0}
                  </td>
                  <td style={{ textAlign: 'center', color: '#c62828' }}>
                    {run.failed_count || 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Summary stats */}
      {runs.length > 0 && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{runs.length}</div>
            <div className="stat-label">Total Runs</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {runs.filter(r => r.status === 'complete').length}
            </div>
            <div className="stat-label">Successful Runs</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {runs.reduce((sum, r) => sum + (r.total_calls || 0), 0)}
            </div>
            <div className="stat-label">Total API Calls</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">
              {runs.reduce((sum, r) => sum + (r.success_count || 0), 0)}
            </div>
            <div className="stat-label">Successful Responses</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RunHistory;