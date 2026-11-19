/* Poll the text files the switcher writes. OBS browser sources cannot use file://. */
(function () {
  const query = new URLSearchParams(location.search);
  const interval = Number(query.get("interval") || 500);
  if (query.get("ticker") === "0") document.body.classList.add("no-ticker");
  if (query.get("headline") === "0") document.body.classList.add("no-headline");
  if (query.get("clear") === "1") document.body.classList.remove("matte");
  if (query.get("preview") === "1") document.body.classList.add("matte");

  const warn = document.getElementById("warn");
  let failures = 0;

  async function pull(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    return (await response.text()).replace(/^\uFEFF/, "").replace(/\s+$/u, "");
  }

  function setText(node, value) {
    if (node.dataset.value === value) return;
    node.dataset.value = value;
    node.textContent = value;
    node.classList.remove("tick");
    void node.offsetWidth;
    node.classList.add("tick");
    if (node.dataset.hideEmpty === "1" && node.parentElement) {
      node.parentElement.classList.toggle("is-empty", value === "");
    }
  }

  function updateTicker(node, value) {
    if (node.dataset.value === value) return;
    node.dataset.value = value;
    node.textContent = "";
    if (!value) return;
    const track = document.createElement("div");
    track.id = "ticker-track";
    const seconds = Math.max(24, Math.round(value.length * 0.18));
    track.style.animation = `ticker-move ${seconds}s linear infinite`;
    for (let copy = 0; copy < 2; copy += 1) {
      const chunk = document.createElement("span");
      chunk.className = "ticker-chunk";
      chunk.textContent = value + "    ";
      track.appendChild(chunk);
    }
    node.appendChild(track);
  }

  if (!document.getElementById("ticker-style")) {
    const style = document.createElement("style");
    style.id = "ticker-style";
    style.textContent = "@keyframes ticker-move { from { transform: translateX(0); } to { transform: translateX(-50%); } }";
    document.head.appendChild(style);
  }

  async function tickFiles() {
    const nodes = document.querySelectorAll("[data-file]");
    let missed = 0;
    for (const node of nodes) {
      try {
        const value = await pull(node.dataset.file);
        if (node.dataset.role === "ticker") updateTicker(node, value);
        else setText(node, value);
      } catch (error) {
        missed += 1;
      }
    }
    failures = missed ? failures + 1 : 0;
    if (warn) warn.classList.toggle("on", failures >= 4);
  }

  async function tickClock() {
    const clock = document.getElementById("clock");
    if (!clock) return;
    try {
      const timezone = clock.dataset.tz || (await pull(clock.dataset.tzFile));
      const zone = clock.dataset.zone || (await pull(clock.dataset.zoneFile));
      if (timezone) clock.dataset.tz = timezone;
      if (zone) clock.dataset.zone = zone;
      if (!timezone) return;
      const formatted = new Intl.DateTimeFormat("en-US", {
        timeZone: timezone,
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }).format(new Date());
      setText(clock, zone ? `${formatted} ${zone}` : formatted);
    } catch (error) {
      /* Clock is optional. A bad timezone string just leaves it blank. */
    }
  }

  tickFiles();
  tickClock();
  setInterval(tickFiles, interval);
  setInterval(tickClock, 1000);
})();
