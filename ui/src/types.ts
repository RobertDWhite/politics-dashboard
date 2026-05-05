export interface CategoryDef {
  key: string;
  label: string;
}

export interface PublicConfig {
  title: string;
  categories: CategoryDef[];
  twitter: {
    enabled: boolean;
    categories: CategoryDef[];
  };
}

export interface Article {
  id: string;
  title: string;
  url: string;
  published: number;
  source: string;
  content: string;
  category: string;
  summary: string | null;
}

export type Accounts = Record<string, string[]>;

export interface AccountSummary {
  summary: string | null;
  updated_at: number | null;
}

export type AccountSummaries = Record<string, Record<string, AccountSummary>>;

export interface Digest {
  text: string;
  updated_at: number;
  article_count: number;
}
