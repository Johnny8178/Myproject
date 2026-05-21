const state = {
  token: localStorage.getItem("grid_token") || "",
  user: null,
  loading: false,
  scheduleTimer: null,
  scheduleRunning: false,
  lastSlotKey: "",
};

const API_BASE = String(window.GRID_API_BASE || "").replace(/\/$/, "");

const dom = {
  sessionText: document.getElementById("sessionText"),
  statusText: document.getElementById("statusText"),
  authPanel: document.getElementById("authPanel"),
  workspacePanel: document.getElementById("workspacePanel"),
  resultPanel: document.getElementById("resultPanel"),
  scheduleLogPanel: document.getElementById("scheduleLogPanel"),
  loginForm: document.getElementById("loginForm"),
  registerForm: document.getElementById("registerForm"),
  loginTabBtn: document.getElementById("loginTabBtn"),
  registerTabBtn: document.getElementById("registerTabBtn"),
  loginAccountInput: document.getElementById("loginAccountInput"),
  loginPasswordInput: document.getElementById("loginPasswordInput"),
  registerAccountInput: document.getElementById("registerAccountInput"),
  registerPasswordInput: document.getElementById("registerPasswordInput"),
  registerConfirmPasswordInput: document.getElementById("registerConfirmPasswordInput"),
  authHint: document.getElementById("authHint"),
  accountIdInput: document.getElementById("accountIdInput"),
  availableCashInput: document.getElementById("availableCashInput"),
  intervalInput: document.getElementById("intervalInput"),
  marketStartInput: document.getElementById("marketStartInput"),
  marketEndInput: document.getElementById("marketEndInput"),
  positionsBody: document.getElementById("positionsBody"),
  summaryBox: document.getElementById("summaryBox"),
  resultList: document.getElementById("resultList"),
  scheduleLogList: document.getElementById("scheduleLogList"),
  scheduleStateText: document.getElementById("scheduleStateText"),
  nextRunText: document.getElementById("nextRunText"),
  slotsText: document.getElementById("slotsText"),
  loginBtn: document.getElementById("loginBtn"),
  registerBtn: document.getElementById("registerBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  loadPositionsBtn: document.getElementById("loadPositionsBtn"),
  addRowBtn: document.getElementById("addRowBtn"),
  savePositionsBtn: document.getElementById("savePositionsBtn"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  runNowBtn: document.getElementById("runNowBtn"),
  startScheduleBtn: document.getElementById("startScheduleBtn"),
  stopScheduleBtn: document.getElementById("stopScheduleBtn"),
  rowTemplate: document.getElementById("rowTemplate"),
};

function setStatus(text) {
  dom.statusText.textContent = text;
  if (dom.authHint && !dom.authPanel.classList.contains("hidden")) {
    dom.authHint.textContent = text;
    dom.authHint.classList.toggle("active", Boolean(text));
  }
}

function setAuthMode(mode) {
  const isRegister = mode === "register";
  dom.loginForm.classList.toggle("hidden", isRegister);
  dom.registerForm.classList.toggle("hidden", !isRegister);
  dom.loginTabBtn.classList.toggle("active", !isRegister);
  dom.registerTabBtn.classList.toggle("active", isRegister);
  dom.loginTabBtn.setAttribute("aria-selected", String(!isRegister));
  dom.registerTabBtn.setAttribute("aria-selected", String(isRegister));
  setStatus(isRegister ? "创建新账号后会自动登录。" : "输入账号和密码登录。");
}

function setLoading(flag) {
  state.loading = flag;
  [
    dom.loginBtn,
    dom.registerBtn,
    dom.loadPositionsBtn,
    dom.addRowBtn,
    dom.savePositionsBtn,
    dom.analyzeBtn,
    dom.runNowBtn,
    dom.logoutBtn,
  ].forEach((btn) => {
    btn.disabled = flag;
  });
  updateScheduleButtons();
}

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "-";
  return Number(v).toFixed(digits);
}

async function api(path, options = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    options.headers || {}
  );
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

function renderSession() {
  if (state.token && state.user) {
    dom.sessionText.textContent = `已登录: ${state.user.phone} (${state.user.role})`;
    dom.authPanel.classList.add("hidden");
    dom.workspacePanel.classList.remove("hidden");
  } else {
    dom.sessionText.textContent = "未登录";
    dom.authPanel.classList.remove("hidden");
    dom.workspacePanel.classList.add("hidden");
    dom.resultPanel.classList.add("hidden");
    dom.scheduleLogPanel.classList.add("hidden");
  }
  updateScheduleMeta();
}

function addPositionRow(item = {}) {
  const frag = dom.rowTemplate.content.cloneNode(true);
  const tr = frag.querySelector("tr");
  tr.querySelectorAll("input,select").forEach((el) => {
    const key = el.getAttribute("data-k");
    if (!key) return;
    if (item[key] !== undefined && item[key] !== null) {
      el.value = item[key];
    }
  });
  tr.querySelector(".remove-row-btn").addEventListener("click", () => {
    tr.remove();
  });
  dom.positionsBody.appendChild(frag);
}

function collectPositions() {
  const rows = [...dom.positionsBody.querySelectorAll("tr")];
  return rows
    .map((tr) => {
      const obj = {};
      tr.querySelectorAll("input,select").forEach((el) => {
        const key = el.getAttribute("data-k");
        if (!key) return;
        obj[key] = el.value;
      });
      return {
        symbol: (obj.symbol || "").trim(),
        stock_name: (obj.stock_name || "").trim(),
        quantity: Number(obj.quantity || 0),
        avg_cost: Number(obj.avg_cost || 0),
        stop_loss: Number(obj.stop_loss || 0),
        target_price: Number(obj.target_price || 0),
        grid_step_pct: Number(obj.grid_step_pct || 2),
        grid_buy_shares: Number(obj.grid_buy_shares || 100),
        grid_sell_shares: Number(obj.grid_sell_shares || 100),
        max_layers: Number(obj.max_layers || 6),
        base_price_mode: (obj.base_price_mode || "current").trim(),
        cash_reserve_pct: Number(obj.cash_reserve_pct || 20),
        position_cap_shares: Number(obj.position_cap_shares || 100000),
      };
    })
    .filter((x) => x.symbol);
}

function renderSummary(summary, availableCash) {
  dom.summaryBox.innerHTML = "";
  const cards = [
    { k: "可用现金", v: fmtNum(availableCash, 2) },
    { k: "持仓数量", v: String(summary.positions || 0) },
    { k: "持仓市值", v: fmtNum(summary.market_value || 0, 2) },
    { k: "浮盈亏", v: fmtNum(summary.unrealized_pnl || 0, 2) },
  ];
  cards.forEach((item) => {
    const div = document.createElement("div");
    div.className = "metric";
    div.innerHTML = `<div class="k">${item.k}</div><div class="v">${item.v}</div>`;
    dom.summaryBox.appendChild(div);
  });
}

function riskBadge(level) {
  const raw = String(level || "").toLowerCase();
  if (raw.includes("high")) return "high";
  if (raw.includes("medium")) return "medium";
  return "low";
}

function renderResultCard(item) {
  const card = document.createElement("article");
  card.className = "result-card";
  if (item.error) {
    card.innerHTML = `
      <div class="card-head">
        <strong>${item.symbol}</strong>
        <span class="badge high">error</span>
      </div>
      <div class="card-body"><div>${item.error}</div></div>
    `;
    return card;
  }

  const metrics = item.wave_metrics || {};
  const phase = item.phase_position || {};
  const advice = item.grid_advice || {};
  const riskLevel = phase.risk_level || (advice.risk_flags?.length ? "high" : "low");
  const riskClass = riskBadge(riskLevel);
  const levels = advice.levels || [];

  const levelsRows = levels
    .map(
      (lv) => `
      <tr>
        <td>${lv.level}</td>
        <td>${fmtNum(lv.buy_price, 3)}</td>
        <td>${fmtNum(lv.sell_price, 3)}</td>
        <td>${lv.buy_shares}</td>
        <td>${lv.sell_shares}</td>
        <td>${fmtNum(lv.buy_capital, 2)}</td>
      </tr>
    `
    )
    .join("");

  const riskFlags = advice.risk_flags || [];

  card.innerHTML = `
    <div class="card-head">
      <strong>${item.symbol} ${item.stock_name || ""}</strong>
      <span class="badge ${riskClass}">${riskLevel || "unknown"}</span>
    </div>
    <div class="card-body">
      <div>
        <div class="kv-grid">
          <div>现价: <strong>${fmtNum(item.current_price, 3)}</strong></div>
          <div>成本: <strong>${fmtNum(item.avg_cost, 3)}</strong></div>
          <div>市值: <strong>${fmtNum(item.market_value, 2)}</strong></div>
          <div>浮盈亏: <strong>${fmtNum(item.unrealized_pnl, 2)}</strong></div>
          <div>主力波中轴: <strong>${fmtNum(metrics.current_wave, 3)}</strong></div>
          <div>偏离率%: <strong>${fmtNum(metrics.deviation_pct, 3)}</strong></div>
          <div>波动率%: <strong>${fmtNum(metrics.volatility_pct, 3)}</strong></div>
          <div>象限: <strong>${phase.quadrant_name || "-"}</strong></div>
          <div>建议间距%: <strong>${fmtNum(advice.recommended_grid_step_pct, 3)}</strong></div>
          <div>建议买入股数: <strong>${advice.recommended_buy_shares ?? "-"}</strong></div>
          <div>建议卖出股数: <strong>${advice.recommended_sell_shares ?? "-"}</strong></div>
          <div>总买入资金: <strong>${fmtNum(advice.total_buy_capital, 2)}</strong></div>
        </div>
        <div><strong>建议说明:</strong> ${phase.grid_hint || "基于当前波动和偏离率自动生成建议。"}</div>
        <div class="levels">
          <table>
            <thead>
              <tr><th>层</th><th>买入价</th><th>卖出价</th><th>买入股数</th><th>卖出股数</th><th>买入资金</th></tr>
            </thead>
            <tbody>${levelsRows}</tbody>
          </table>
        </div>
        ${riskFlags.length ? `<div class="risk"><strong>风险提示:</strong> ${riskFlags.join(" ; ")}</div>` : ""}
      </div>
      <div class="image-box">
        ${item.image_url ? `<img src="${item.image_url}" alt="${item.symbol} 分析图" />` : "<div>暂无分析图</div>"}
      </div>
    </div>
  `;
  return card;
}

function renderResults(payload) {
  dom.resultPanel.classList.remove("hidden");
  renderSummary(payload.summary || {}, payload.available_cash || 0);
  dom.resultList.innerHTML = "";
  (payload.results || []).forEach((item) => {
    dom.resultList.appendChild(renderResultCard(item));
  });
}

function parseClock(value) {
  const [hour, minute] = String(value || "00:00").split(":").map(Number);
  return hour * 60 + minute;
}

function formatClock(totalMinutes) {
  const hour = Math.floor(totalMinutes / 60);
  const minute = totalMinutes % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function todayAt(totalMinutes) {
  const d = new Date();
  d.setHours(Math.floor(totalMinutes / 60), totalMinutes % 60, 0, 0);
  return d;
}

function getScheduleSlots() {
  const start = parseClock(dom.marketStartInput.value || "09:30");
  const end = parseClock(dom.marketEndInput.value || "15:30");
  const interval = Number(dom.intervalInput.value || 30);
  const slots = [];
  for (let t = start; t <= end; t += interval) {
    slots.push(t);
  }
  return slots;
}

function getNextSlot(now = new Date()) {
  return getScheduleSlots()
    .map(todayAt)
    .find((slot) => slot >= now) || null;
}

function updateScheduleButtons() {
  if (!dom.startScheduleBtn) return;
  dom.startScheduleBtn.disabled = state.loading || state.scheduleRunning;
  dom.stopScheduleBtn.disabled = state.loading || !state.scheduleRunning;
}

function updateScheduleMeta() {
  const slots = getScheduleSlots().map(formatClock);
  const next = getNextSlot();
  dom.scheduleStateText.textContent = state.scheduleRunning ? "运行中" : "未启动";
  dom.nextRunText.textContent = `下一次: ${next ? next.toLocaleTimeString("zh-CN", { hour12: false }) : "今日已结束"}`;
  dom.slotsText.textContent = `时间点: ${slots.join(" / ")}`;
  updateScheduleButtons();
}

function buildScheduleSnapshot(payload, label) {
  const log = document.createElement("article");
  log.className = "schedule-log";
  const summary = payload.summary || {};
  const lines = (payload.results || [])
    .map((item) => {
      if (item.error) return `<li><strong>${item.symbol}</strong>: ${item.error}</li>`;
      const advice = item.grid_advice || {};
      const phase = item.phase_position || {};
      return `
        <li>
          <strong>${item.symbol} ${item.stock_name || ""}</strong>
          现价 ${fmtNum(item.current_price, 3)}，
          间距 ${fmtNum(advice.recommended_grid_step_pct, 3)}%，
          买 ${advice.recommended_buy_shares ?? "-"} 股，
          卖 ${advice.recommended_sell_shares ?? "-"} 股，
          基准 ${fmtNum(advice.base_price, 3)}，
          ${phase.grid_hint || "按当前波动和偏离率生成。"}
        </li>
      `;
    })
    .join("");
  log.innerHTML = `
    <div class="schedule-log-head">
      <strong>${label}</strong>
      <span>${payload.run_at || new Date().toLocaleString("zh-CN", { hour12: false })}</span>
    </div>
    <div class="schedule-log-summary">
      持仓 ${summary.positions || 0} 只，市值 ${fmtNum(summary.market_value || 0, 2)}，浮盈亏 ${fmtNum(summary.unrealized_pnl || 0, 2)}
    </div>
    <ul>${lines}</ul>
  `;
  return log;
}

async function runTimedAnalyze(label = "手动触发") {
  const account_id = dom.accountIdInput.value.trim() || "acc_main";
  const available_cash = Number(dom.availableCashInput.value || 0);
  const positions = collectPositions();
  if (!positions.length) {
    setStatus("请先录入至少一只股票");
    return null;
  }
  setLoading(true);
  setStatus(`${label}计算中...`);
  try {
    const payload = await api("/api/portfolio/timed-analyze", {
      method: "POST",
      body: JSON.stringify({ account_id, available_cash, positions }),
    });
    renderResults(payload);
    dom.scheduleLogPanel.classList.remove("hidden");
    dom.scheduleLogList.prepend(buildScheduleSnapshot(payload, label));
    setStatus(`${label}完成: ${payload.results?.length || 0} 只股票`);
    return payload;
  } catch (err) {
    setStatus(`${label}失败: ${err.message}`);
    return null;
  } finally {
    setLoading(false);
    updateScheduleMeta();
  }
}

async function checkSchedule() {
  if (!state.scheduleRunning || state.loading) return;
  const now = new Date();
  const start = todayAt(parseClock(dom.marketStartInput.value || "09:30"));
  const end = todayAt(parseClock(dom.marketEndInput.value || "15:30"));
  if (now < start || now > end) {
    updateScheduleMeta();
    return;
  }
  const matched = getScheduleSlots()
    .map(todayAt)
    .find((slot) => Math.abs(now - slot) < 60 * 1000);
  if (!matched) return;
  const slotKey = matched.toISOString().slice(0, 16);
  if (state.lastSlotKey === slotKey) return;
  state.lastSlotKey = slotKey;
  await runTimedAnalyze(`定时 ${matched.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })}`);
}

function startSchedule() {
  state.scheduleRunning = true;
  state.lastSlotKey = "";
  if (state.scheduleTimer) window.clearInterval(state.scheduleTimer);
  state.scheduleTimer = window.setInterval(checkSchedule, 30 * 1000);
  updateScheduleMeta();
  setStatus("盘中自动计算已启动");
  checkSchedule();
}

function stopSchedule() {
  state.scheduleRunning = false;
  if (state.scheduleTimer) window.clearInterval(state.scheduleTimer);
  state.scheduleTimer = null;
  updateScheduleMeta();
  setStatus("盘中自动计算已停止");
}

async function bootstrapSession() {
  renderSession();
  if (!state.token) return;
  try {
    const me = await api("/api/me");
    state.user = me.user;
    renderSession();
    await loadPositions();
  } catch {
    state.token = "";
    state.user = null;
    localStorage.removeItem("grid_token");
    renderSession();
  }
}

async function loginLike(mode) {
  const form = mode === "register" ? dom.registerForm : dom.loginForm;
  const phone = (mode === "register" ? dom.registerAccountInput : dom.loginAccountInput).value.trim();
  const password = (mode === "register" ? dom.registerPasswordInput : dom.loginPasswordInput).value;
  if (mode === "register") {
    const confirmPassword = dom.registerConfirmPasswordInput.value;
    dom.registerConfirmPasswordInput.setCustomValidity(
      password === confirmPassword ? "" : "两次密码必须一致。"
    );
  }
  form.classList.add("was-validated");
  if (!form.checkValidity()) {
    setStatus("请检查账号和密码格式。");
    return;
  }
  setLoading(true);
  setStatus(mode === "register" ? "正在注册..." : "正在登录...");
  try {
    if (mode === "register") {
      await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ phone, password }),
      });
      setStatus("注册成功，正在登录...");
    }
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ phone, password }),
    });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("grid_token", state.token);
    renderSession();
    form.classList.remove("was-validated");
    setStatus("登录成功");
    await loadPositions();
  } catch (err) {
    setStatus(`登录失败: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function logout() {
  setLoading(true);
  try {
    if (state.token) {
      await api("/api/auth/logout", { method: "POST" });
    }
  } catch {
  } finally {
    state.token = "";
    state.user = null;
    localStorage.removeItem("grid_token");
    renderSession();
    dom.positionsBody.innerHTML = "";
    dom.resultList.innerHTML = "";
    dom.summaryBox.innerHTML = "";
    dom.resultPanel.classList.add("hidden");
    dom.scheduleLogList.innerHTML = "";
    dom.scheduleLogPanel.classList.add("hidden");
    stopSchedule();
    setStatus("已退出登录");
    setLoading(false);
  }
}

async function loadPositions() {
  setLoading(true);
  try {
    const account_id = dom.accountIdInput.value.trim() || "acc_main";
    const data = await api(`/api/positions?account_id=${encodeURIComponent(account_id)}`);
    dom.availableCashInput.value = data.available_cash || 0;
    dom.positionsBody.innerHTML = "";
    (data.positions || []).forEach(addPositionRow);
    if (!data.positions || !data.positions.length) {
      addPositionRow();
    }
    setStatus(`已读取持仓: ${data.positions?.length || 0} 条`);
  } catch (err) {
    setStatus(`读取持仓失败: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function savePositions() {
  const account_id = dom.accountIdInput.value.trim() || "acc_main";
  const available_cash = Number(dom.availableCashInput.value || 0);
  const positions = collectPositions();
  setLoading(true);
  try {
    const data = await api("/api/positions/upsert", {
      method: "POST",
      body: JSON.stringify({ account_id, available_cash, positions }),
    });
    setStatus(`保存成功: ${data.saved_count} 条`);
  } catch (err) {
    setStatus(`保存失败: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

async function analyze() {
  const account_id = dom.accountIdInput.value.trim() || "acc_main";
  const available_cash = Number(dom.availableCashInput.value || 0);
  const positions = collectPositions();
  if (!positions.length) {
    setStatus("请先录入至少一只股票");
    return;
  }
  setLoading(true);
  setStatus("分析中，请稍候...");
  try {
    const payload = await api("/api/portfolio/analyze", {
      method: "POST",
      body: JSON.stringify({ account_id, available_cash, positions }),
    });
    renderResults(payload);
    setStatus(`分析完成: ${payload.results?.length || 0} 只股票`);
  } catch (err) {
    setStatus(`分析失败: ${err.message}`);
  } finally {
    setLoading(false);
  }
}

dom.loginTabBtn.addEventListener("click", () => setAuthMode("login"));
dom.registerTabBtn.addEventListener("click", () => setAuthMode("register"));
dom.loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginLike("login");
});
dom.registerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loginLike("register");
});
[dom.registerPasswordInput, dom.registerConfirmPasswordInput].forEach((el) => {
  el.addEventListener("input", () => {
    dom.registerConfirmPasswordInput.setCustomValidity("");
  });
});
dom.logoutBtn.addEventListener("click", logout);
dom.loadPositionsBtn.addEventListener("click", loadPositions);
dom.savePositionsBtn.addEventListener("click", savePositions);
dom.analyzeBtn.addEventListener("click", analyze);
dom.addRowBtn.addEventListener("click", () => addPositionRow());
dom.runNowBtn.addEventListener("click", () => runTimedAnalyze("立即"));
dom.startScheduleBtn.addEventListener("click", startSchedule);
dom.stopScheduleBtn.addEventListener("click", stopSchedule);
[dom.intervalInput, dom.marketStartInput, dom.marketEndInput].forEach((el) => {
  el.addEventListener("change", updateScheduleMeta);
});

bootstrapSession();
updateScheduleMeta();
setAuthMode("login");
