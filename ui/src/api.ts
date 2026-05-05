import type { Article, Accounts, AccountSummaries, Digest, PublicConfig } from './types';

export async function fetchConfig(): Promise<PublicConfig> {
  const resp = await fetch('/api/config');
  if (!resp.ok) throw new Error(`Config fetch failed: ${resp.status}`);
  return resp.json();
}

export async function fetchArticles(): Promise<Article[]> {
  const resp = await fetch('/api/articles?limit=150');
  if (!resp.ok) throw new Error(`Articles fetch failed: ${resp.status}`);
  return resp.json();
}

export async function fetchAccounts(): Promise<Accounts> {
  const resp = await fetch('/api/accounts');
  if (!resp.ok) throw new Error(`Accounts fetch failed: ${resp.status}`);
  return resp.json();
}

export async function fetchSummaries(): Promise<AccountSummaries> {
  const resp = await fetch('/api/accounts/summaries');
  if (!resp.ok) throw new Error(`Summaries fetch failed: ${resp.status}`);
  return resp.json();
}

export async function fetchDigest(): Promise<Digest | null> {
  const resp = await fetch('/api/accounts/digest');
  if (!resp.ok) return null;
  const data = await resp.json();
  return data.text ? data : null;
}

export async function triggerRefresh(): Promise<void> {
  const resp = await fetch('/api/refresh', { method: 'POST' });
  if (!resp.ok) throw new Error(`Refresh failed: ${resp.status}`);
}
