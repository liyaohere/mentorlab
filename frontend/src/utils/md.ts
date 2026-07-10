// By Xilan
const esc = (s: string): string =>
  s.replace(
    /[&<>]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] as string,
  );

// Render bold (**...**) and italic (*...*) safely
export function renderMd(src: string): string {
  const re = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let out = "",
    last = 0,
    m;

  while ((m = re.exec(src))) {
    out += esc(src.slice(last, m.index));
    out +=
      m[1] !== undefined
        ? "<strong>" + esc(m[1]) + "</strong>"
        : "<em>" + esc(m[2]) + "</em>";
    last = re.lastIndex;
  }

  out += esc(src.slice(last));
  return out;
}
