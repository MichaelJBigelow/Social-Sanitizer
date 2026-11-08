// Scrolls a scanned comment into view and pulses it. __ID__ is replaced from Python.
(() => {
  const el = document.querySelector('[data-ss-id="__ID__"]');
  if (!el) return false;
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.removeAttribute("data-ss-focus");
  void el.offsetWidth; // restart the animation
  el.setAttribute("data-ss-focus", "");
  setTimeout(() => el.removeAttribute("data-ss-focus"), 3000);
  return true;
})()
