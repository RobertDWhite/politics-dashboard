import { useState } from 'react';
import type { Accounts, AccountSummaries, CategoryDef } from '../types';
import { Markdown } from './Markdown';

interface Props {
  categories: CategoryDef[];
  accounts: Accounts;
  summaries: AccountSummaries | null;
  nitterEmbedBase: string;  // e.g. https://nitter.example.com — for the iframe view
}

export function XPanel({ categories, accounts, summaries, nitterEmbedBase }: Props) {
  const firstKey = categories[0]?.key ?? '';
  const [category, setCategory] = useState(firstKey);
  const [handle, setHandle] = useState('');
  const [summaryOpen, setSummaryOpen] = useState(false);

  const activeCat = category || firstKey;
  const handles = accounts[activeCat] ?? [];
  const activeHandle = handle && handles.includes(handle) ? handle : (handles[0] ?? '');
  const activeSummary = summaries?.[activeCat]?.[activeHandle];

  return (
    <>
      <div className="x-cat-tabs">
        {categories.map(cat => (
          <button
            key={cat.key}
            className={`x-cat-btn ${activeCat === cat.key ? 'active' : ''}`}
            onClick={() => { setCategory(cat.key); setHandle(''); }}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="x-handles">
        {handles.map(h => (
          <button
            key={h}
            className={`x-handle-btn ${activeHandle === h ? 'active' : ''}`}
            onClick={() => setHandle(h)}
          >
            @{h}
          </button>
        ))}
      </div>

      {activeHandle && activeSummary && (
        <div className={`x-summary ${summaryOpen ? 'open' : 'collapsed'}`}>
          <button
            className="x-summary-toggle"
            onClick={() => setSummaryOpen(o => !o)}
          >
            <span className="x-summary-label">
              <span className="x-summary-icon">{summaryOpen ? '▼' : '▶'}</span>
              AI Summary — @{activeHandle}
            </span>
            {!summaryOpen && activeSummary.summary && (
              <span className="x-summary-preview">{activeSummary.summary.slice(0, 80)}…</span>
            )}
          </button>
          {summaryOpen && (
            activeSummary.summary
              ? <Markdown text={activeSummary.summary} className="x-summary-text" />
              : <p className="x-summary-pending">Generating summary…</p>
          )}
        </div>
      )}

      {nitterEmbedBase && (
        <div className="x-embed-container">
          {activeHandle && (
            <iframe
              key={activeHandle}
              src={`${nitterEmbedBase.replace(/\/$/, '')}/${activeHandle}`}
              width="100%"
              height="100%"
              style={{ border: 'none', colorScheme: 'dark' }}
              title={`@${activeHandle} via Nitter`}
            />
          )}
        </div>
      )}
    </>
  );
}
