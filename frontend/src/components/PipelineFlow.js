import React, { useState } from 'react';
import axios from 'axios';

const API = 'http://127.0.0.1:8000/api';

const STEPS = [
    { id: 1, label: 'Crawl + Extract BIO'  },
    { id: 2, label: 'Review BIO'           },
    { id: 3, label: 'Generate Prompts'     },
    { id: 4, label: 'Select + Fire'        },
];

function PipelineFlow({ brand, onResultsReady }) {
    const [step, setStep]           = useState(1);
    const [bio, setBio]             = useState(null);
    const [prompts, setPrompts]     = useState([]);
    const [selected, setSelected]   = useState([]);
    const [results, setResults]     = useState(null);
    const [loading, setLoading]     = useState(false);
    const [message, setMessage]     = useState('');

    const runCrawlAndBio = async () => {
        setLoading(true);
        setMessage('🔍 Crawling brand website and extracting BIO...');
        try {
            const res = await axios.post(`${API}/pipeline/crawl-and-bio`, {
                brand_id: brand.id,
            });
            setBio(res.data.bio);
            setStep(2);
            setMessage('✅ BIO extracted! Please review below before continuing.');
        } catch (e) {
            setMessage('❌ Crawl failed. Check terminal for details.');
        }
        setLoading(false);
    };

    const generatePrompts = async () => {
        setLoading(true);
        setMessage('📝 Generating prompts from SERP signals...');
        try {
            const res = await axios.post(`${API}/pipeline/generate-prompts`, {
                brand_id: brand.id,
            });
            setPrompts(res.data.prompts);
            setStep(4);
            setMessage(`✅ ${res.data.total_prompts} prompts generated! Select 5–10 to fire.`);
        } catch (e) {
            setMessage('❌ Prompt generation failed. Check terminal for details.');
        }
        setLoading(false);
    };

    const toggleSelect = (id) => {
        if (selected.includes(id)) {
            setSelected(selected.filter(s => s !== id));
        } else {
            if (selected.length >= 10) {
                setMessage('⚠️ Maximum 10 prompts allowed.');
                return;
            }
            setSelected([...selected, id]);
        }
    };

    const fireSelected = async () => {
        if (selected.length === 0) {
            setMessage('⚠️ Please select at least 1 prompt.');
            return;
        }
        setLoading(true);
        setMessage(`🔥 Firing ${selected.length} prompts at Gemini...`);
        try {
            const res = await axios.post(`${API}/pipeline/fire-selected`, {
                brand_id:   brand.id,
                prompt_ids: selected,
            });
            setResults(res.data.results);
            setMessage(`✅ Done! ${res.data.total} prompts fired at Gemini.`);
            if (onResultsReady) onResultsReady(res.data.results);
        } catch (e) {
            setMessage('❌ Firing failed. Check terminal for details.');
        }
        setLoading(false);
    };

    return (
        <div>
            <div style={{
                display:       'flex',
                gap:           0,
                marginBottom:  24,
                background:    'white',
                borderRadius:  12,
                padding:       '16px 24px',
                boxShadow:     '0 2px 8px rgba(0,0,0,0.08)',
            }}>
                {STEPS.map((s, i) => (
                    <div key={s.id} style={{
                        flex:       1,
                        display:    'flex',
                        alignItems: 'center',
                        gap:        8,
                    }}>
                        <div style={{
                            width:        28,
                            height:       28,
                            borderRadius: '50%',
                            background:   step >= s.id ? '#e94560' : '#eee',
                            color:        step >= s.id ? 'white' : '#aaa',
                            display:      'flex',
                            alignItems:   'center',
                            justifyContent: 'center',
                            fontSize:     13,
                            fontWeight:   700,
                            flexShrink:   0,
                        }}>
                            {step > s.id ? '✓' : s.id}
                        </div>
                        <span style={{
                            fontSize:   13,
                            color:      step >= s.id ? '#1a1a2e' : '#aaa',
                            fontWeight: step === s.id ? 600 : 400,
                        }}>
                            {s.label}
                        </span>
                        {i < STEPS.length - 1 && (
                            <div style={{
                                flex:       1,
                                height:     2,
                                background: step > s.id ? '#e94560' : '#eee',
                                margin:     '0 8px',
                            }} />
                        )}
                    </div>
                ))}
            </div>

            {message && (
                <div style={{
                    padding:      '10px 16px',
                    background:   '#f0f7ff',
                    borderRadius: 8,
                    marginBottom: 16,
                    fontSize:     14,
                }}>
                    {message}
                </div>
            )}

            {step === 1 && (
                <div className="card">
                    <h2>Step 1 — Crawl Brand Website</h2>
                    <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>
                        We'll crawl <strong>{brand.domain}</strong> (top 100 pages),
                        extract clean text, and use Gemini to build a Brand Intelligence Object (BIO).
                    </p>
                    <button
                        className="btn btn-primary"
                        onClick={runCrawlAndBio}
                        disabled={loading}
                    >
                        {loading ? '⏳ Crawling...' : '🔍 Start Crawl + Extract BIO'}
                    </button>
                </div>
            )}

            {step === 2 && bio && (
                <div>
                    <div className="card">
                        <h2>Step 2 — Review Brand Intelligence Object</h2>
                        <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>
                            Gemini extracted this BIO from {brand.domain}.
                            Review it and confirm before generating prompts.
                        </p>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <BioField label="Brand Name"        value={bio.brand_name} />
                            <BioField label="Price Positioning" value={bio.price_positioning} />
                            <BioField label="Product Categories" value={bio.product_categories?.join(', ')} />
                            <BioField label="Target Personas"   value={bio.target_personas?.join(', ')} />
                            <BioField label="Product Attributes" value={bio.product_attributes?.join(', ')} />
                            <BioField label="Use Cases"         value={bio.use_cases?.join(', ')} />
                            <BioField label="Competitors Found" value={bio.competitor_signals?.join(', ')} />
                            <BioField label="Geo Markets"       value={bio.geo_markets?.join(', ')} />
                            <BioField label="Category Keywords" value={bio.category_keywords?.join(', ')} />
                            {bio.confidence_flags?.length > 0 && (
                                <BioField
                                    label="⚠️ Low Confidence Fields"
                                    value={bio.confidence_flags.join(', ')}
                                    warning
                                />
                            )}
                            {bio._dropped_hallucinations?.length > 0 && (
                                <BioField
                                    label="🚫 Dropped (failed verification)"
                                    value={bio._dropped_hallucinations.map(d => d.value).join(', ')}
                                    warning
                                />
                            )}
                        </div>

                        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
                            <button
                                className="btn btn-primary"
                                onClick={generatePrompts}
                                disabled={loading}
                            >
                                {loading ? '⏳ Generating...' : '✅ BIO looks good — Generate Prompts'}
                            </button>
                            <button
                                className="btn btn-outline"
                                onClick={() => { setStep(1); setBio(null); }}
                            >
                                🔄 Re-crawl
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {step === 4 && prompts.length > 0 && (
                <div>
                    <div className="card">
                        <h2>Step 4 — Select Prompts to Fire</h2>
                        <p style={{ color: '#888', fontSize: 14, marginBottom: 16 }}>
                            {prompts.length} prompts generated. Select 5–10 to fire at Gemini.
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: 13, color: '#888' }}>
                                {selected.length} / 10 selected
                            </span>
                            <button
                                className="btn btn-primary"
                                onClick={fireSelected}
                                disabled={loading || selected.length === 0}
                            >
                                {loading ? '⏳ Firing...' : `🚀 Fire ${selected.length} Prompts at Gemini`}
                            </button>
                        </div>
                    </div>

                    <div className="card">
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
                                            cursor:     'pointer',
                                            background: selected.includes(p.id) ? '#fff3e0' : 'white',
                                        }}
                                    >
                                        <td>
                                            <input
                                                type="checkbox"
                                                checked={selected.includes(p.id)}
                                                onChange={() => toggleSelect(p.id)}
                                                style={{ width: 'auto' }}
                                                onClick={e => e.stopPropagation()}
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

                    {results && (
                        <div className="card">
                            <h2>📊 Gemini Results</h2>
                            <table>
                                <thead>
                                    <tr>
                                        <th>Prompt</th>
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
                                                        {r.brand_source_urls.map((s, j) => (
                                                            <a
                                                                key={j}
                                                                href={s.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                style={{ fontSize: 12, color: '#e94560' }}
                                                                title={s.title || s.url}
                                                            >
                                                                {s.title ? (s.title.length > 30 ? s.title.slice(0, 30) + '…' : s.title) : 'View source'}
                                                            </a>
                                                        ))}
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
                    )}
                </div>
            )}
        </div>
    );
}

function BioField({ label, value, warning }) {
    return (
        <div style={{
            background:   warning ? '#fff3e0' : '#f8f8f8',
            borderRadius: 8,
            padding:      '12px 16px',
        }}>
            <div style={{
                fontSize:     12,
                color:        warning ? '#e65100' : '#888',
                fontWeight:   600,
                marginBottom: 4,
            }}>
                {label}
            </div>
            <div style={{ fontSize: 14, color: '#333' }}>
                {value || '—'}
            </div>
        </div>
    );
}

export default PipelineFlow;