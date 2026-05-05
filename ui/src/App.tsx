import { useCallback, useEffect, useState } from 'react';
import type { Accounts, AccountSummaries, Article, Digest, PublicConfig } from './types';
import {
  fetchAccounts, fetchArticles, fetchConfig, fetchDigest, fetchSummaries, triggerRefresh,
} from './api';
import { ArticleFeed } from './components/ArticleFeed';
import { XPanel } from './components/XPanel';
import { Markdown } from './components/Markdown';
import './App.css';

const NITTER_EMBED_BASE = (
  (import.meta as unknown as { env?: { VITE_NITTER_EMBED_BASE?: string } }).env
    ?.VITE_NITTER_EMBED_BASE ?? ''
);

function formatUpdated(d: Date): string {
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return d.toLocaleTimeString();
}

function formatDigestUpdated(ts: number): string {
  const diff = Math.floor((Date.now() / 1000) - ts);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleString();
}

export default function App() {
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [accounts, setAccounts] = useState<Accounts>({});
  const [summaries, setSummaries] = useState<AccountSummaries | null>(null);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [digestOpen, setDigestOpen] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchConfig().then(c => {
      setConfig(c);
      document.title = c.title;
    }).catch(() => setError(true));
  }, []);

  const load = useCallback(async () => {
    try {
      const [arts, accts, sums, dig] = await Promise.all([
        fetchArticles(),
        fetchAccounts(),
        fetchSummaries().catch(() => null),
        fetchDigest().catch(() => null),
      ]);
      setArticles(arts);
      setAccounts(accts);
      setSummaries(sums);
      setDigest(dig);
      setLastUpdated(new Date());
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerRefresh();
      await load();
    } finally {
      setRefreshing(false);
    }
  };

  const visibleCount =
    filter === 'all' ? articles.length : articles.filter(a => a.category === filter).length;

  if (!config) {
    return <div className="app"><header className="header"><h1>Loading…</h1></header></div>;
  }

  const filters = [{ key: 'all', label: 'All' }, ...config.categories];
  const twitterEnabled = config.twitter.enabled;

  return (
    <div className="app">
      <header className="header">
        <h1>{config.title}</h1>
        <div className="header-meta">
          {error && <span className="error-badge">Error loading</span>}
          {lastUpdated && <span>Updated {formatUpdated(lastUpdated)}</span>}
          <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? '…' : '↻'}
          </button>
        </div>
      </header>

      {digest && (
        <div className={`digest-panel ${digestOpen ? 'open' : 'collapsed'}`}>
          <button className="digest-header" onClick={() => setDigestOpen(o => !o)}>
            <span className="digest-title">
              <span className="digest-icon">{digestOpen ? '▼' : '▶'}</span>
              24-Hour News Digest <span className="digest-ai-tag">(AI Summary)</span>
            </span>
            <span className="digest-meta">
              {digest.article_count} articles · {formatDigestUpdated(digest.updated_at)}
            </span>
          </button>
          {digestOpen && <Markdown text={digest.text} className="digest-text" />}
        </div>
      )}

      <div className="main">
        <div className="feed-panel">
          <div className="feed-toolbar">
            {filters.map(f => (
              <button
                key={f.key}
                className={`filter-btn ${filter === f.key ? 'active' : ''}`}
                onClick={() => setFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
            <span className="article-count">{visibleCount} articles</span>
          </div>
          <div className="feed-scroll">
            <ArticleFeed articles={articles} filter={filter} categories={config.categories} />
          </div>
        </div>

        {twitterEnabled && (
          <div className="x-panel">
            <div className="x-panel-header">
              <span className="x-logo">𝕏</span>
              Live Posts
            </div>
            <XPanel
              categories={config.twitter.categories}
              accounts={accounts}
              summaries={summaries}
              nitterEmbedBase={NITTER_EMBED_BASE}
            />
          </div>
        )}
      </div>
    </div>
  );
}
