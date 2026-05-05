import { useState } from 'react';
import type { Article, CategoryDef } from '../types';

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000) - ts;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function badgeClass(key: string, index: number): string {
  // Two-tone palette: first category uses news color, second uses gov color,
  // additional categories cycle. Stable per category key.
  return index % 2 === 0 ? 'badge-news' : 'badge-gov';
}

interface Props {
  article: Article;
  categories: CategoryDef[];
}

export function ArticleCard({ article, categories }: Props) {
  const [expanded, setExpanded] = useState(false);
  const idx = categories.findIndex(c => c.key === article.category);
  const def = idx >= 0 ? categories[idx] : null;
  const label = def?.label ?? article.category;
  const shortLabel = label.length > 4 ? label.slice(0, 4) : label;

  return (
    <div className="article-card">
      <div className="article-meta">
        <span className={`category-badge ${badgeClass(article.category, idx >= 0 ? idx : 0)}`}>
          {shortLabel}
        </span>
        <span className="article-source">{article.source}</span>
        <span className="article-time">{timeAgo(article.published)}</span>
      </div>

      <a
        className="article-title"
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {article.title}
      </a>

      {article.summary && (
        <>
          <button className="summary-toggle" onClick={() => setExpanded(v => !v)}>
            {expanded ? '▲' : '▼'} AI Summary
          </button>
          {expanded && <p className="summary-text">{article.summary}</p>}
        </>
      )}
    </div>
  );
}
