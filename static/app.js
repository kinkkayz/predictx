const API = "";
const STORAGE_KEY = "predictx_user";

const state = {
  user: null,
  markets: [],
  currentMarket: null,
  filter: "all",
  search: "",
  view: "home",
};

function loadUser() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    try {
      state.user = JSON.parse(raw);
    } catch {
      state.user = null;
    }
  }
}

function saveUser(user) {
  state.user = user;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || "Request failed");
  return data;
}

async function ensureUser() {
  if (state.user?.id) {
    const fresh = await api(`/api/users/${state.user.id}`);
    saveUser({ ...state.user, ...fresh });
    return state.user;
  }
  const created = await api("/api/users", {
    method: "POST",
    body: JSON.stringify({ display_name: "Trader" }),
  });
  saveUser(created);
  return state.user;
}

function formatPct(price) {
  return `${(price * 100).toFixed(1)}%`;
}

function formatMoney(n) {
  return `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function toast(msg, type = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.className = "toast"), 3000);
}

function navigate(view, marketId = null) {
  state.view = view;
  if (marketId) state.selectedMarketId = marketId;
  render();
  if (view === "market" && marketId) loadMarket(marketId);
  if (view === "portfolio") loadPortfolio();
  if (view === "home") loadMarkets();
}

async function loadMarkets() {
  try {
    const params = new URLSearchParams();
    if (state.filter === "open") params.set("status", "open");
    if (state.filter === "resolved") params.set("status", "resolved");
    if (state.search) params.set("q", state.search);
    const qs = params.toString();
    state.markets = await api(`/api/markets${qs ? `?${qs}` : ""}`);
    renderMarkets();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadMarket(id) {
  try {
    state.currentMarket = await api(`/api/markets/${id}`);
    renderMarketDetail();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function loadPortfolio() {
  await ensureUser();
  try {
    const data = await api(`/api/users/${state.user.id}`);
    saveUser({ ...state.user, ...data });
    renderPortfolio(data);
  } catch (e) {
    toast(e.message, "error");
  }
}

function renderMarkets() {
  const grid = document.getElementById("markets-grid");
  if (!state.markets.length) {
    grid.innerHTML = `<div class="empty">No markets found. Create one!</div>`;
    return;
  }
  grid.innerHTML = state.markets
    .map(
      (m) => `
    <article class="market-card" onclick="navigate('market','${m.id}')">
      <div class="card-top">
        <span class="badge">${m.category}</span>
        <span class="status ${m.status}">${m.status}</span>
      </div>
      <h3>${escapeHtml(m.title)}</h3>
      <div class="prob-bar">
        <div class="yes-seg" style="width:${m.yes_price * 100}%"></div>
      </div>
      <div class="prices">
        <button class="price-btn yes" onclick="event.stopPropagation();quickBet('${m.id}','yes')">
          Yes <strong>${formatPct(m.yes_price)}</strong>
        </button>
        <button class="price-btn no" onclick="event.stopPropagation();quickBet('${m.id}','no')">
          No <strong>${formatPct(m.no_price)}</strong>
        </button>
      </div>
      <div class="card-meta">
        <span>Vol ${formatMoney(m.volume)}</span>
        ${m.end_date ? `<span>Ends ${m.end_date}</span>` : ""}
      </div>
    </article>`
    )
    .join("");
}

function renderMarketDetail() {
  const m = state.currentMarket;
  if (!m) return;
  document.getElementById("market-title").textContent = m.title;
  document.getElementById("market-desc").textContent = m.description || "No description.";
  document.getElementById("market-category").textContent = m.category;
  document.getElementById("market-status").textContent = m.status;
  document.getElementById("market-status").className = `status ${m.status}`;
  document.getElementById("yes-price-lg").textContent = formatPct(m.yes_price);
  document.getElementById("no-price-lg").textContent = formatPct(m.no_price);
  document.getElementById("yes-bar").style.width = `${m.yes_price * 100}%`;
  document.getElementById("vol-stat").textContent = formatMoney(m.volume);
  document.getElementById("liq-stat").textContent = formatMoney(m.yes_pool + m.no_pool);

  const resolvePanel = document.getElementById("resolve-panel");
  resolvePanel.style.display = m.status === "open" ? "flex" : "none";

  const resolvedBanner = document.getElementById("resolved-banner");
  if (m.status === "resolved") {
    resolvedBanner.style.display = "block";
    resolvedBanner.textContent = `Resolved: ${m.resolution?.toUpperCase()} won`;
  } else {
    resolvedBanner.style.display = "none";
  }

  const tradeForm = document.getElementById("trade-form");
  tradeForm.style.opacity = m.status === "open" ? "1" : "0.5";
  tradeForm.style.pointerEvents = m.status === "open" ? "auto" : "none";

  const trades = document.getElementById("recent-trades");
  if (!m.recent_trades?.length) {
    trades.innerHTML = '<li class="muted">No trades yet</li>';
  } else {
    trades.innerHTML = m.recent_trades
      .map(
        (t) =>
          `<li><span class="${t.side}">${t.side.toUpperCase()}</span> ${t.shares.toFixed(2)} shares @ ${formatPct(t.price)} · ${formatMoney(t.amount)}</li>`
      )
      .join("");
  }
}

function renderPortfolio(data) {
  document.getElementById("portfolio-balance").textContent = formatMoney(data.balance);
  const tbody = document.getElementById("positions-body");
  if (!data.positions?.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="muted">No open positions. Browse markets to trade.</td></tr>`;
    return;
  }
  tbody.innerHTML = data.positions
    .map(
      (p) => `
    <tr onclick="navigate('market','${p.market_id}')" class="clickable">
      <td>${escapeHtml(p.title)}</td>
      <td><span class="side-tag ${p.side}">${p.side.toUpperCase()}</span></td>
      <td>${p.shares.toFixed(2)}</td>
      <td>${formatPct(p.avg_price)}</td>
      <td>${formatPct(p.current_price)}</td>
      <td>${formatMoney(p.value)} <span class="muted">/ ${formatMoney(p.cost)}</span></td>
    </tr>`
    )
    .join("");
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

let selectedSide = "yes";

function selectSide(side) {
  selectedSide = side;
  document.getElementById("btn-yes").classList.toggle("active", side === "yes");
  document.getElementById("btn-no").classList.toggle("active", side === "no");
}

async function placeBet() {
  await ensureUser();
  const amount = parseFloat(document.getElementById("bet-amount").value);
  if (!amount || amount <= 0) return toast("Enter a valid amount", "error");

  try {
    const res = await api(`/api/markets/${state.currentMarket.id}/bet`, {
      method: "POST",
      body: JSON.stringify({ user_id: state.user.id, side: selectedSide, amount }),
    });
    saveUser({ ...state.user, balance: res.balance });
    state.currentMarket = res.market;
    document.getElementById("header-balance").textContent = formatMoney(res.balance);
    renderMarketDetail();
    toast(`Bought ${res.trade.shares.toFixed(2)} ${selectedSide.toUpperCase()} shares`, "success");
  } catch (e) {
    toast(e.message, "error");
  }
}

async function quickBet(marketId, side) {
  navigate("market", marketId);
  await loadMarket(marketId);
  selectSide(side);
  document.getElementById("bet-amount").focus();
}

async function createMarket(e) {
  e.preventDefault();
  const form = e.target;
  const body = {
    title: form.title.value,
    description: form.description.value,
    category: form.category.value,
    end_date: form.end_date.value || null,
  };
  try {
    const m = await api("/api/markets", { method: "POST", body: JSON.stringify(body) });
    form.reset();
    document.getElementById("create-modal").classList.remove("open");
    toast("Market created!", "success");
    navigate("market", m.id);
  } catch (err) {
    toast(err.message, "error");
  }
}

async function resolveMarket(resolution) {
  if (!confirm(`Resolve this market as ${resolution.toUpperCase()}? This pays out winners.`)) return;
  try {
    await api(`/api/markets/${state.currentMarket.id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolution }),
    });
    toast(`Market resolved: ${resolution.toUpperCase()}`, "success");
    loadMarket(state.currentMarket.id);
  } catch (e) {
    toast(e.message, "error");
  }
}

function render() {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${state.view}`)?.classList.add("active");
  document.querySelectorAll(".nav-link").forEach((a) => {
    a.classList.toggle("active", a.dataset.view === state.view);
  });
}

function openCreateModal() {
  document.getElementById("create-modal").classList.add("open");
}

function closeCreateModal() {
  document.getElementById("create-modal").classList.remove("open");
}

async function init() {
  loadUser();
  await ensureUser();
  document.getElementById("header-balance").textContent = formatMoney(state.user.balance);
  document.getElementById("header-name").textContent = state.user.display_name;

  document.getElementById("search-input").addEventListener("input", (e) => {
    state.search = e.target.value;
    loadMarkets();
  });

  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filter = btn.dataset.filter;
      loadMarkets();
    });
  });

  selectSide("yes");
  navigate("home");
}

init();
