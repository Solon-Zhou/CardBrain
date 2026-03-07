/**
 * home.js — 首頁：Agent 聊天
 */

async function HomePage() {
  return `
    <div class="agent-section">
      <div class="agent-messages" id="agentMessages">
        <div class="agent-bubble bot">
          <div class="agent-avatar">🧠</div>
          <div class="agent-text">嗨！我是 CardBrain Agent，告訴我你的消費情境，我幫你找最划算的卡。<br><br>試試看：「星巴克 300」、「全聯 2000」、「日本旅遊 10萬」</div>
        </div>
      </div>
      <div class="agent-quick-tags" id="agentQuickTags">
        <span class="agent-tag" data-msg="星巴克 300">☕ 星巴克 300</span>
        <span class="agent-tag" data-msg="全聯 2000">🛒 全聯 2000</span>
        <span class="agent-tag" data-msg="日本旅遊 10萬">✈️ 日本 10萬</span>
        <span class="agent-tag" data-msg="加油 1500">⛽ 加油 1500</span>
      </div>
      <div class="agent-input-bar">
        <input class="agent-input" id="agentInput"
          type="text" placeholder="輸入消費情境，例如「星巴克 300」" autocomplete="off">
        <button class="agent-send-btn" id="agentSendBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </div>
  `;
}

HomePage.init = () => {
  const messagesEl = document.getElementById("agentMessages");
  const agentInput = document.getElementById("agentInput");
  const sendBtn = document.getElementById("agentSendBtn");
  const quickTags = document.getElementById("agentQuickTags");
  let _sending = false;

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `agent-bubble ${role}`;
    if (role === "bot") {
      bubble.innerHTML = `<div class="agent-avatar">🧠</div><div class="agent-text">${text}</div>`;
    } else {
      bubble.innerHTML = `<div class="agent-text">${escapeHtml(text)}</div>`;
    }
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  function addTyping() {
    const bubble = document.createElement("div");
    bubble.className = "agent-bubble bot";
    bubble.id = "agentTyping";
    bubble.innerHTML = `<div class="agent-avatar">🧠</div><div class="agent-text agent-typing"><span></span><span></span><span></span></div>`;
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("agentTyping");
    if (el) el.remove();
  }

  function formatReply(text) {
    return escapeHtml(text).replace(/\n/g, "<br>");
  }

  async function sendMessage(text) {
    if (_sending || !text.trim()) return;
    _sending = true;
    agentInput.value = "";
    sendBtn.disabled = true;

    quickTags.style.display = "none";

    addBubble("user", text);
    addTyping();

    try {
      const res = await API.agent(text);
      removeTyping();
      const replyHtml = formatReply(res.reply || "抱歉，我無法理解你的問題。");

      let extraHtml = "";
      if (res.data && !res.data.error) {
        extraHtml = _buildDataCard(res.mode, res.data);
      }

      addBubble("bot", replyHtml + extraHtml);
    } catch (err) {
      removeTyping();
      addBubble("bot", "抱歉，發生了一點問題，請稍後再試。");
    }

    _sending = false;
    sendBtn.disabled = false;
    agentInput.focus();
  }

  agentInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.isComposing) {
      e.preventDefault();
      sendMessage(agentInput.value);
    }
  });
  sendBtn.addEventListener("click", () => sendMessage(agentInput.value));
  quickTags.addEventListener("click", (e) => {
    const tag = e.target.closest(".agent-tag");
    if (tag) sendMessage(tag.dataset.msg);
  });
};

// ── 精算結果卡片渲染 ──
function _buildDataCard(mode, data) {
  if (mode === "instant") return _buildInstantCard(data);
  if (mode === "plan") return _buildPlanCard(data);
  if (mode === "regret") return _buildRegretCard(data);
  return "";
}

function _buildInstantCard(data) {
  const results = data.results || [];
  if (!results.length) return "";
  const best = results[0];
  const rtype = best.reward_type || "cashback";
  const unit = rtype === "cashback" ? "回饋" : (rtype === "miles" ? "哩程" : "點");

  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-best">
    <div class="agent-data-best-label">最佳推薦</div>
    <div class="agent-data-best-name">${best.bank_name} ${best.card_name}</div>
    <div class="agent-data-best-reward">$${(best.actual_reward || 0).toFixed(1)} <small>${unit}</small></div>
    <div class="agent-data-best-rate">${best.reward_rate}%</div>
  </div>`;

  if (results.length > 1) {
    html += `<div class="agent-data-others">`;
    results.slice(1, 4).forEach((r, i) => {
      html += `<div class="agent-data-other">
        <span class="agent-data-rank">#${i + 2}</span>
        <span class="agent-data-other-name">${r.bank_name} ${r.card_name}</span>
        <span class="agent-data-other-reward">$${(r.actual_reward || 0).toFixed(1)}</span>
      </div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

function _buildPlanCard(data) {
  const cards = data.cards_to_bring || [];
  const savings = data.total_savings || 0;
  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-plan-hero">
    <span>預估省下</span>
    <strong>$${savings.toFixed(0)}</strong>
  </div>`;
  if (cards.length) {
    html += `<div class="agent-data-bring">帶卡清單：`;
    cards.forEach((c) => {
      const usage = (c.usage || []).join("、");
      html += `<div class="agent-data-bring-item">${c.card} → ${usage}</div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

function _buildRegretCard(data) {
  const regret = data.total_regret || 0;
  const yourReward = data.total_your_reward || 0;
  const bestReward = data.total_best_reward || 0;
  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-regret-summary">
    <div><span>你的回饋</span><strong>$${yourReward.toFixed(1)}</strong></div>
    <div><span>最佳回饋</span><strong class="green">$${bestReward.toFixed(1)}</strong></div>
    <div><span>少賺</span><strong class="red">$${regret.toFixed(1)}</strong></div>
  </div>`;
  html += `</div>`;
  return html;
}
