function parseHM(value) {
  const m = String(value || "").trim().match(/^(\d{1,2}):(\d{2})$/);
  if (!m) return { h: 9, min: 0 };
  return { h: Math.min(23, Math.max(0, Number(m[1]))), min: Math.min(59, Math.max(0, Number(m[2]))) };
}

function fmtHM(h, min) {
  return String(h).padStart(2, "0") + ":" + String(min).padStart(2, "0");
}

function AnalogClock(host, opts) {
  opts = opts || {};
  let { h, min } = parseHM(opts.value);
  let drag = null;
  host.classList.add("clock");
  host.innerHTML = `
    <svg class="clock-svg" viewBox="0 0 200 200" role="img" aria-label="Analog time">
      <circle class="clock-face" cx="100" cy="100" r="94" />
      <g class="clock-ticks"></g>
      <line class="clock-hand hour" x1="100" y1="100" x2="100" y2="58" />
      <line class="clock-hand minute" x1="100" y1="100" x2="100" y2="28" />
      <circle class="clock-cap" cx="100" cy="100" r="6" />
    </svg>
    <div class="clock-read">${fmtHM(h, min)}</div>
    <div class="clock-ampm">
      <button type="button" class="ghost am">AM</button>
      <button type="button" class="ghost pm">PM</button>
    </div>`;
  const svg = host.querySelector(".clock-svg");
  const ticks = host.querySelector(".clock-ticks");
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
    const inner = i % 3 === 0 ? 78 : 84;
    const x1 = 100 + Math.cos(a) * inner;
    const y1 = 100 + Math.sin(a) * inner;
    const x2 = 100 + Math.cos(a) * 90;
    const y2 = 100 + Math.sin(a) * 90;
    ticks.insertAdjacentHTML("beforeend", `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" />`);
  }
  const hourEl = host.querySelector(".clock-hand.hour");
  const minEl = host.querySelector(".clock-hand.minute");
  const read = host.querySelector(".clock-read");
  const amBtn = host.querySelector(".am");
  const pmBtn = host.querySelector(".pm");

  function emit() {
    const v = fmtHM(h, min);
    read.textContent = v;
    amBtn.classList.toggle("on", h < 12);
    pmBtn.classList.toggle("on", h >= 12);
    if (opts.onChange) opts.onChange(v);
  }

  function draw() {
    const minA = (min / 60) * Math.PI * 2 - Math.PI / 2;
    const hourA = (((h % 12) + min / 60) / 12) * Math.PI * 2 - Math.PI / 2;
    hourEl.setAttribute("x2", String(100 + Math.cos(hourA) * 46));
    hourEl.setAttribute("y2", String(100 + Math.sin(hourA) * 46));
    minEl.setAttribute("x2", String(100 + Math.cos(minA) * 72));
    minEl.setAttribute("y2", String(100 + Math.sin(minA) * 72));
    emit();
  }

  function angleFromEvent(e) {
    const pt = e.touches ? e.touches[0] : e;
    const box = svg.getBoundingClientRect();
    const x = pt.clientX - (box.left + box.width / 2);
    const y = pt.clientY - (box.top + box.height / 2);
    const dist = Math.sqrt(x * x + y * y) / (box.width / 2);
    let deg = (Math.atan2(y, x) * 180) / Math.PI + 90;
    if (deg < 0) deg += 360;
    return { deg, dist };
  }

  function apply(e) {
    const { deg, dist } = angleFromEvent(e);
    if (!drag) drag = dist < 0.48 ? "hour" : "min";
    if (drag === "min") {
      min = Math.round(deg / 6) % 60;
    } else {
      const hour12 = Math.round(deg / 30) % 12;
      const pm = h >= 12;
      h = hour12 % 12 + (pm ? 12 : 0);
      if (hour12 === 0) h = pm ? 12 : 0;
    }
    draw();
  }

  function start(e) {
    e.preventDefault();
    drag = null;
    apply(e);
    window.addEventListener("mousemove", apply);
    window.addEventListener("touchmove", apply, { passive: false });
    window.addEventListener("mouseup", stop);
    window.addEventListener("touchend", stop);
  }
  function stop() {
    drag = null;
    window.removeEventListener("mousemove", apply);
    window.removeEventListener("touchmove", apply);
    window.removeEventListener("mouseup", stop);
    window.removeEventListener("touchend", stop);
  }

  svg.addEventListener("mousedown", start);
  svg.addEventListener("touchstart", start, { passive: false });
  amBtn.onclick = () => { if (h >= 12) h -= 12; draw(); };
  pmBtn.onclick = () => { if (h < 12) h += 12; draw(); };
  draw();
  return {
    value() { return fmtHM(h, min); },
    set(v) { ({ h, min } = parseHM(v)); draw(); },
  };
}

function ClockPop(anchor, value, onChange) {
  document.querySelectorAll(".clock-pop").forEach((n) => n.remove());
  const pop = document.createElement("div");
  pop.className = "clock-pop card";
  const face = document.createElement("div");
  pop.appendChild(face);
  document.body.appendChild(pop);
  const clock = AnalogClock(face, {
    value,
    onChange: (v) => { onChange(v); },
  });
  const box = anchor.getBoundingClientRect();
  const left = Math.min(window.innerWidth - 240, Math.max(8, box.left));
  const top = Math.min(window.innerHeight - 280, box.bottom + 8);
  pop.style.left = left + "px";
  pop.style.top = top + "px";
  function close(e) {
    if (e && pop.contains(e.target)) return;
    pop.remove();
    document.removeEventListener("mousedown", close);
  }
  setTimeout(() => document.addEventListener("mousedown", close), 0);
  return clock;
}
