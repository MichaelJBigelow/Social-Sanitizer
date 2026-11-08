// Marks scanned comments on the page. __VERDICTS__ is replaced from Python with a JSON
// object of {commentId: true|false} (true = flagged). Returns how many were flagged.
(() => {
  const verdicts = __VERDICTS__;

  if (!document.getElementById("ss-style")) {
    const style = document.createElement("style");
    style.id = "ss-style";
    style.textContent = `
      [data-ss-state="flagged"] {
        outline: 2px solid #e5484d !important;
        outline-offset: 2px;
        background-color: rgba(229, 72, 77, 0.10) !important;
        border-radius: 6px;
      }
      [data-ss-focus] { animation: ss-pulse 0.9s ease-out 3; }
      @keyframes ss-pulse {
        from { box-shadow: 0 0 0 0 rgba(229, 72, 77, 0.8); }
        to   { box-shadow: 0 0 0 14px rgba(229, 72, 77, 0); }
      }`;
    document.head.appendChild(style);
  }

  let flagged = 0;
  for (const el of document.querySelectorAll("[data-ss-id]")) {
    const id = el.getAttribute("data-ss-id");
    if (!(id in verdicts)) {
      el.removeAttribute("data-ss-state");
      continue;
    }
    el.setAttribute("data-ss-state", verdicts[id] ? "flagged" : "clean");
    if (verdicts[id]) flagged++;
  }
  return flagged;
})()
