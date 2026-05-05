import type { Article, CategoryDef } from '../types';
import { ArticleCard } from './ArticleCard';

interface Props {
  articles: Article[];
  filter: string;  // 'all' or a category key
  categories: CategoryDef[];
}

export function ArticleFeed({ articles, filter, categories }: Props) {
  const visible = filter === 'all' ? articles : articles.filter(a => a.category === filter);

  if (visible.length === 0) {
    return <p className="feed-empty">No articles yet</p>;
  }

  return (
    <>
      {visible.map(article => (
        <ArticleCard key={article.id} article={article} categories={categories} />
      ))}
    </>
  );
}
