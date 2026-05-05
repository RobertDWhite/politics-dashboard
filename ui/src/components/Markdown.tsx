import { type ReactNode } from 'react';

type Block =
  | { type: 'header'; content: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] }
  | { type: 'para'; content: string };

function parse(text: string): Block[] {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let para: string[] = [];
  let ul: string[] | null = null;
  let ol: string[] | null = null;

  const flushPara = () => {
    if (para.length) {
      blocks.push({ type: 'para', content: para.join(' ') });
      para = [];
    }
  };
  const flushUl = () => { if (ul) { blocks.push({ type: 'ul', items: ul }); ul = null; } };
  const flushOl = () => { if (ol) { blocks.push({ type: 'ol', items: ol }); ol = null; } };
  const flushAll = () => { flushPara(); flushUl(); flushOl(); };

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) { flushAll(); continue; }

    const headerMd = line.match(/^#{1,6}\s+(.+)$/);
    if (headerMd) { flushAll(); blocks.push({ type: 'header', content: headerMd[1] }); continue; }

    const headerBold = line.match(/^\*\*([^*]+):\*\*\s*$/);
    if (headerBold) { flushAll(); blocks.push({ type: 'header', content: headerBold[1] }); continue; }

    const ulItem = line.match(/^[-*•]\s+(.+)$/);
    if (ulItem) {
      flushPara(); flushOl();
      if (!ul) ul = [];
      ul.push(ulItem[1]);
      continue;
    }

    const olItem = line.match(/^\d+\.\s+(.+)$/);
    if (olItem) {
      flushPara(); flushUl();
      if (!ol) ol = [];
      ol.push(olItem[1]);
      continue;
    }

    flushUl(); flushOl();
    para.push(line);
  }
  flushAll();
  return blocks;
}

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) parts.push(<strong key={key++}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith('`')) parts.push(<code key={key++}>{tok.slice(1, -1)}</code>);
    else parts.push(<em key={key++}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export function Markdown({ text, className = '' }: { text: string; className?: string }) {
  const blocks = parse(text);
  return (
    <div className={`md ${className}`}>
      {blocks.map((b, i) => {
        if (b.type === 'header') return <h4 key={i} className="md-h">{inline(b.content)}</h4>;
        if (b.type === 'ul') {
          return (
            <ul key={i} className="md-list md-ul">
              {b.items.map((item, j) => <li key={j}>{inline(item)}</li>)}
            </ul>
          );
        }
        if (b.type === 'ol') {
          return (
            <ol key={i} className="md-list md-ol">
              {b.items.map((item, j) => <li key={j}>{inline(item)}</li>)}
            </ol>
          );
        }
        return <p key={i} className="md-p">{inline(b.content)}</p>;
      })}
    </div>
  );
}
