/* RE4 Classic Trainer — landing page interactions
   Arabic / English switching, scroll effects, counters, gallery. */

document.body.classList.add("js");

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* ============================== language ================================= */
const STORE_KEY = "re4-lang";

function applyLanguage(lang, remember = true) {
  const dict = (window.I18N && (window.I18N[lang] || window.I18N.ar)) || {};
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";

  $$("[data-i18n]").forEach((el) => {
    const value = dict[el.dataset.i18n];
    if (value !== undefined) el.innerHTML = value;
  });

  if (dict["meta.title"]) document.title = dict["meta.title"];
  const desc = document.querySelector('meta[name="description"]');
  if (desc && dict["meta.desc"]) desc.setAttribute("content", dict["meta.desc"]);

  const langBtn = $("#langBtn");
  if (langBtn) {
    const label = langBtn.querySelector("span");
    if (label) label.textContent = dict["nav.lang"] || "";
    langBtn.title = dict["nav.langTitle"] || "";
    langBtn.dataset.next = lang === "ar" ? "en" : "ar";
  }
  if (remember) {
    try { localStorage.setItem(STORE_KEY, lang); } catch (e) {}
  }
}

let currentLang = "ar";
try {
  const url = new URLSearchParams(location.search).get("lang");
  currentLang = url || localStorage.getItem(STORE_KEY) || "ar";
} catch (e) {}
applyLanguage(currentLang, false);

const langBtn = $("#langBtn");
if (langBtn) {
  langBtn.addEventListener("click", () => {
    currentLang = langBtn.dataset.next || (currentLang === "ar" ? "en" : "ar");
    applyLanguage(currentLang);
    document.body.classList.add("lang-swap");
    window.setTimeout(() => document.body.classList.remove("lang-swap"), 320);
  });
}

/* ============================ sticky header ============================== */
const nav = $("#nav");
const progress = $("#progress");

function onScroll() {
  const y = window.scrollY || document.documentElement.scrollTop;
  nav.classList.toggle("on", y > 12);
  const max = document.documentElement.scrollHeight - window.innerHeight;
  progress.style.transform = `scaleX(${max > 0 ? Math.min(1, y / max) : 0})`;
  spy();
}
window.addEventListener("scroll", onScroll, { passive: true });

/* =============================== mobile menu ============================= */
const burger = $("#burger");
if (burger) {
  burger.addEventListener("click", () => document.body.classList.toggle("menu-open"));
  $$("#links a").forEach((a) => a.addEventListener("click", () => document.body.classList.remove("menu-open")));
}

/* =============================== scroll spy ============================== */
const sections = ["features", "how", "why", "gallery", "faq", "fixes", "download"];
function spy() {
  const y = window.scrollY + 140;
  let active = "";
  sections.forEach((id) => {
    const el = document.getElementById(id);
    if (el && el.offsetTop <= y) active = id;
  });
  $$("#links a").forEach((a) => {
    a.classList.toggle("active", a.getAttribute("href") === `#${active}`);
  });
}

/* ========================== reveal on scroll ============================= */
function revealVisible() {
  const vh = window.innerHeight || document.documentElement.clientHeight;
  $$(".reveal:not(.in)").forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.top < vh - 30 && r.bottom > -30) el.classList.add("in");
  });
}
window.addEventListener("scroll", revealVisible, { passive: true });
window.addEventListener("resize", revealVisible);
window.addEventListener("load", () => window.setTimeout(revealVisible, 60));
revealVisible();

/* ============================== counters ================================= */
function runCounters() {
  $$(".count").forEach((el) => {
    if (el.dataset.done) return;
    const r = el.getBoundingClientRect();
    if (r.top > (window.innerHeight || 0) - 40) return;
    el.dataset.done = "1";
    const target = parseFloat(el.dataset.count || "0");
    if (!target) { el.textContent = "0"; return; }
    const steps = 34;
    let i = 0;
    const tick = () => {
      i += 1;
      const eased = 1 - Math.pow(1 - i / steps, 3);
      el.textContent = String(Math.round(target * eased));
      if (i < steps) window.setTimeout(tick, 18);
      else el.textContent = String(target);
    };
    tick();
  });
}
window.addEventListener("scroll", runCounters, { passive: true });
window.addEventListener("load", () => window.setTimeout(runCounters, 120));

/* =============================== gallery ================================= */
const tabs = $$(".tab");
const shots = $$(".shot");
let shotIndex = 0;

function showShot(index, { scroll = false } = {}) {
  shotIndex = (index + shots.length) % shots.length;
  shots.forEach((s, i) => s.classList.toggle("on", i === shotIndex));
  tabs.forEach((t, i) => t.classList.toggle("on", i === shotIndex));
  if (scroll) {
    const box = $(".shots");
    if (box) box.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

tabs.forEach((tab, i) => tab.addEventListener("click", () => showShot(i)));

document.addEventListener("keydown", (event) => {
  if (!location.hash.includes("gallery")) return;
  if (event.key === "ArrowLeft")  showShot(shotIndex + 1);
  if (event.key === "ArrowRight") showShot(shotIndex - 1);
});

/* ============================== misc ==================================== */
const year = $("#year");
if (year) year.textContent = String(new Date().getFullYear());

onScroll();
