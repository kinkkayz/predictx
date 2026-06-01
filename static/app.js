const API = "";

const state = {
  user: null,
  markets: [],
  currentMarket: null,
  filter: "all",
  search: "",
  view: "home",
  authTab: "login",
};

function apiErrorMessage(data, fallback = "Request failed") {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg;
  return fallback;
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(apiErrorMessage(data));
    err.status = res.status;
    throw err;
  }
  return data;
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

function showAuth() {
  document.getElementById("view-auth").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
  state.user = null;
}

function showApp() {
  document.getElementById("view-auth").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");
  updateHeader();
}

function updateHeader() {
  if (!state.user) return;
  document.getElementById("header-balance").textContent = formatMoney(state.user.balance);
  document.getElementById("header-name").textContent = state.user.display_name;
}

function switchAuthTab(tab) {
  state.authTab = tab;
  document.querySelectorAll(".auth-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tab);
  });
  document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
  document.getElementById("signup-form").classList.toggle("hidden", tab !== "signup");
}

async function loadAuthConfig() {
  try {
    const cfg = await api("/api/auth/config");
    if (cfg.google_enabled) {
      document.getElementById("google-auth-block").classList.remove("hidden");
      document.getElementById("google-btn").classList.remove("hidden");
    }
  } catch {
    /* ignore */
  }
}

async function fetchSession() {
  try {
    const user = await api("/api/auth/me");
    state.user = user;
    return true;
  } catch (e) {
    if (e.status === 401) return false;
    throw e;
  }
}

async function submitLogin(e) {
  e.preventDefault();
  const form = e.target;
  try {
    const user = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value,
        password: form.password.value,
      }),
    });
    state.user = user;
    form.reset();
    showApp();
    navigate("home");
    toast("Welcome back!", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function submitSignup(e) {
  e.preventDefault();
  const form = e.target;
  try {
    const user = await api("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value,
        password: form.password.value,
        display_name: form.display_name.value,
      }),
    });
    state.user = user;
    form.reset();
    showApp();
    navigate("home");
    toast("Account created — $1,000 demo credits added!", "success");
  } catch (err) {
    toast(err.message, "error");
  }
}

async function logout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
  showAuth();
  switchAuthTab("login");
  toast("Logged out", "info");
}

function navigate(view, marketId = null) {
  if (!state.user) {
    showAuth();
    return;
  }
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
    if (e.status === 401) return showAuth();
    toast(e.message, "error");
  }
}

async function loadMarket(id) {
  try {
    state.currentMarket = await api(`/api/markets/${id}`);
    renderMarketDetail();
  } catch (e) {
    if (e.status === 401) return showAuth();
    toast(e.message, "error");
  }
}

async function loadPortfolio() {
  try {
    const data = await api("/api/portfolio");
    state.user = { ...state.user, ...data };
    updateHeader();
    renderPortfolio(data);
  } catch (e) {
    if (e.status === 401) return showAuth();
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
  const amount = parseFloat(document.getElementById("bet-amount").value);
  if (!amount || amount <= 0) return toast("Enter a valid amount", "error");

  try {
    const res = await api(`/api/markets/${state.currentMarket.id}/bet`, {
      method: "POST",
      body: JSON.stringify({ side: selectedSide, amount }),
    });
    state.user.balance = res.balance;
    state.currentMarket = res.market;
    updateHeader();
    renderMarketDetail();
    toast(`Bought ${res.trade.shares.toFixed(2)} ${selectedSide.toUpperCase()} shares`, "success");
  } catch (e) {
    if (e.status === 401) return showAuth();
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
    if (err.status === 401) return showAuth();
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
    const me = await api("/api/auth/me");
    state.user.balance = me.balance;
    updateHeader();
    loadMarket(state.currentMarket.id);
  } catch (e) {
    if (e.status === 401) return showAuth();
    toast(e.message, "error");
  }
}

function render() {
  document.querySelectorAll("#app-shell .view").forEach((v) => v.classList.remove("active"));
  document.getElementById(`view-${state.view}`)?.classList.add("active");
  document.querySelectorAll(".nav-link").forEach((a) => {
    a.classList.toggle("active", a.dataset.view === state.view);
  });
}

function openCreateModal() {
  if (!state.user) return showAuth();
  document.getElementById("create-modal").classList.add("open");
}

function closeCreateModal() {
  document.getElementById("create-modal").classList.remove("open");
}

function handleAuthQueryParams() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("logged_in") === "1") {
    toast("Signed in with Google!", "success");
    window.history.replaceState({}, "", "/");
  }
  const err = params.get("auth_error");
  if (err) {
    toast("Google sign-in failed. Try again or use email.", "error");
    window.history.replaceState({}, "", "/");
  }
}

async function init() {
  handleAuthQueryParams();
  await loadAuthConfig();
  switchAuthTab("login");

  document.getElementById("search-input")?.addEventListener("input", (e) => {
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

  try {
    const ok = await fetchSession();
    if (ok) {
      showApp();
      navigate("home");
    } else {
      showAuth();
    }
  } catch (e) {
    toast(e.message, "error");
    showAuth();
  }
}

init();
