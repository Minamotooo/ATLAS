import { Fragment } from "react";
import katex from "katex";

// Splits a line of text into alternating plain-text / math segments.
// Supports $$...$$ (display math) and $...$ (inline math) delimiters, which is
// what the question bank's LaTeX content uses (see data-gen/question_gen_common.py).
function splitMath(line) {
  const parts = [];
  const regex = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(line)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: line.slice(lastIndex, match.index) });
    }
    if (match[1] !== undefined) {
      parts.push({ type: "math", value: match[1], display: true });
    } else {
      parts.push({ type: "math", value: match[2], display: false });
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < line.length) {
    parts.push({ type: "text", value: line.slice(lastIndex) });
  }
  return parts;
}

function renderMath(source, display, key) {
  let html;
  try {
    html = katex.renderToString(source, {
      throwOnError: false,
      displayMode: display,
    });
  } catch {
    // Fall back to the raw source (with delimiters) so broken LaTeX is at
    // least visible instead of silently vanishing.
    const raw = display ? `$$${source}$$` : `$${source}$`;
    return <span key={key}>{raw}</span>;
  }
  return <span key={key} dangerouslySetInnerHTML={{ __html: html }} />;
}

/**
 * Renders question/option/explanation text that mixes plain (Bangla) text
 * with inline ($...$) or display ($$...$$) LaTeX, and literal newlines.
 *
 * Some generated content stores newlines as a literal two-character "\n"
 * rather than an actual line break, so both forms are normalized here.
 */
export default function MathText({ text, className }) {
  if (text === null || text === undefined || text === "") return null;

  const normalized = String(text).replace(/\\n/g, "\n");
  const lines = normalized.split("\n");

  return (
    <span className={className}>
      {lines.map((line, lineIdx) => (
        <Fragment key={lineIdx}>
          {lineIdx > 0 && <br />}
          {splitMath(line).map((part, partIdx) =>
            part.type === "math" ? (
              renderMath(part.value, part.display, `${lineIdx}-${partIdx}`)
            ) : (
              <span key={`${lineIdx}-${partIdx}`}>{part.value}</span>
            )
          )}
        </Fragment>
      ))}
    </span>
  );
}
