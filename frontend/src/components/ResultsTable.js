import React from 'react';

/**
 * Shared results table — used by both PromptSelector.js and
 * PipelineFlow.js, which previously had this exact table (Mentioned /
 * Cited / Form / Source columns, same styling, same unconfirmed-source
 * handling) duplicated verbatim in two files. Any future fix or
 * feature to this table now only needs to happen once, here.
 */
const GEO_LABELS = { IN: '🇮🇳 IN', AE: '🇦🇪 AE', GB: '🇬🇧 GB' };

function ResultsTable({ results, title = '📊 Results' }) {
  if (!results || results.length === 0) return null;

  return (
    <div className="card">
      <h2>{title}</h2>
      <table>
        <thead>
          <tr>
            <th>Prompt</th>
            <th>Country</th>
            <th>Mentioned?</th>
            <th>Cited?</th>
            <th>Form</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
            <tr key={i}>
              <td style={{ maxWidth: 300 }}>{r.prompt_text}</td>
              <td>{GEO_LABELS[r.geo] || r.geo || '—'}</td>
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
              <td>
                {r.brand_source_urls && r.brand_source_urls.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {r.brand_source_urls.map((s, j) => {
                      const isUnconfirmed = s.matched_by === 'unconfirmed';
                      return (
                        <a
                          key={j}
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: 12,
                            color: isUnconfirmed ? '#999' : '#e94560',
                            fontStyle: isUnconfirmed ? 'italic' : 'normal',
                          }}
                          title={
                            isUnconfirmed
                              ? `Possible source (not confirmed as the exact citation) — ${s.title || s.url}`
                              : (s.title || s.url)
                          }
                        >
                          {isUnconfirmed ? '? ' : ''}
                          {s.title ? (s.title.length > 30 ? s.title.slice(0, 30) + '…' : s.title) : 'View source'}
                        </a>
                      );
                    })}
                  </div>
                ) : (
                  <span style={{ color: '#bbb', fontSize: 12 }}>—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ResultsTable;