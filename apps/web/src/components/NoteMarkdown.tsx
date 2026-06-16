"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * Renders note markdown. Obsidian-style [[wikilinks]] are not valid markdown, so
 * we pre-process them into real links to the in-app note viewer before handing
 * the text to react-markdown.
 */
function linkifyWikilinks(content: string): string {
  return content.replace(/\[\[([^\]]+?)\]\]/g, (_m, raw: string) => {
    const [targetRaw, aliasRaw] = raw.split("|");
    const target = targetRaw.trim();
    const slug = target
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .replace(/[\s-]+/g, "_")
      .replace(/^_+|_+$/g, "");
    const label = (aliasRaw ?? target).trim();
    return `[${label}](/notes/${slug})`;
  });
}

const components: Components = {
  a({ href, children, ...props }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  },
};

export default function NoteMarkdown({ content }: { content: string }) {
  return (
    <div className="prose-note" data-testid="note-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {linkifyWikilinks(content)}
      </ReactMarkdown>
    </div>
  );
}
