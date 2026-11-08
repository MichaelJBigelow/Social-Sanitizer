// Finds comments on the current page and tags each comment's container element with
// data-ss-id so later scripts (highlight, scroll) can find it again.
//
// Instagram's class names are obfuscated and change often, so this relies on structure
// that has stayed stable: a comment is the smallest element that holds
//   1. a link whose text is the author's username (href "/<username>/"),
//   2. a <time> element, and
//   3. a span/div with dir="auto" holding the comment text.
//
// Returns a JSON string: {url, owner, comments: [{id, author, text}]}.
(() => {
  const USERNAME_HREF = /^\/([A-Za-z0-9._]{1,30})\/$/;
  const UI_TEXT = /^(reply|replies|like|likes|see translation|hide replies|view (all )?\d* ?(more )?repl(y|ies).*|—+.*|\d+\s*[smhdwy]|\d+ (likes?|replies?)|edited|author|pinned)$/i;
  const MAX_DEPTH = 12;

  function hash(str) {
    let h = 5381;
    for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0;
    return (h >>> 0).toString(36);
  }

  // A username link shows the username as its text. Avatar links (image only) don't.
  function usernameOf(a) {
    const m = (a.getAttribute("href") || "").match(USERNAME_HREF);
    if (!m) return null;
    return a.textContent.trim() === m[1] ? m[1] : null;
  }

  function commentTextIn(container, authorLink, author) {
    let best = null;
    for (const el of container.querySelectorAll('[dir="auto"]')) {
      if (authorLink.contains(el) || el.closest("time, button, [role=button]")) continue;
      const text = el.innerText.trim();
      if (!text || text === author || UI_TEXT.test(text)) continue;
      if (!best || text.length > best.text.length) best = { el, text };
    }
    return best;
  }

  let owner = null;
  for (const header of document.querySelectorAll("article header, main header")) {
    for (const a of header.querySelectorAll("a[href]")) {
      owner = usernameOf(a);
      if (owner) break;
    }
    if (owner) break;
  }

  const seen = new Set();
  const byId = new Map();
  for (const link of document.querySelectorAll("a[href]")) {
    const author = usernameOf(link);
    if (!author || link.closest("header")) continue;

    let node = link.parentElement;
    for (let depth = 0; node && depth < MAX_DEPTH; depth++, node = node.parentElement) {
      const times = node.querySelectorAll("time").length;
      if (times === 0) continue;
      if (times > 1) break; // climbed past this comment into a thread of several
      const found = commentTextIn(node, link, author);
      if (!found) continue;
      if (!seen.has(node)) {
        seen.add(node);
        const id = hash(author + "\n" + found.text);
        node.setAttribute("data-ss-id", id);
        if (!byId.has(id)) byId.set(id, { id, author, text: found.text });
      }
      break;
    }
  }

  return JSON.stringify({ url: location.href, owner, comments: [...byId.values()] });
})()
