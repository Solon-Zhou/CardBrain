/**
 * home.js — 首頁：Agent 聊天
 */

const AGENT_AVATAR_SRC = "/static/avatar.png";

function _agentAvatarHtml() {
  return `<div class="agent-avatar"><img class="agent-avatar-img" src="${AGENT_AVATAR_SRC}" alt="CardBrain Agent" decoding="async"></div>`;
}

async function HomePage() {
  return `
    <div class="agent-section">
      <div class="agent-messages" id="agentMessages">
        <div class="agent-bubble bot agent-welcome">
          ${_agentAvatarHtml()}
          <div class="agent-text">
            <p class="agent-welcome-title">嗨！我是 CardBrain Agent，告訴我你的消費情境，我幫你找最划算的卡。</p>
            <p class="agent-welcome-hint">試試看：「星巴克 300」、「全聯 2000」、「日本旅遊 10萬」</p>
          </div>
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
  const pageContainer = document.getElementById("page-container");
  if (pageContainer) pageContainer.classList.add("is-agent-page");

  const messagesEl = document.getElementById("agentMessages");
  const agentInput = document.getElementById("agentInput");
  const sendBtn = document.getElementById("agentSendBtn");
  const quickTags = document.getElementById("agentQuickTags");
  let _sending = false;
  let _chatHistory = [];
  const _MAX_HISTORY = 30;

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `agent-bubble ${role}`;
    if (role === "bot") {
      bubble.innerHTML = `${_agentAvatarHtml()}<div class="agent-text">${text}</div>`;
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
    bubble.innerHTML = `${_agentAvatarHtml()}<div class="agent-text agent-typing"><span></span><span></span><span></span></div>`;
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

  function buildToolCards(toolResults) {
    if (!toolResults || !toolResults.length) return "";
    let html = "";
    for (const tr of toolResults) {
      const result = tr.result;
      if (!result || result.error) continue;
      if (tr.name === "instant_recommend") {
        html += _buildInstantCard(result);
      } else if (tr.name === "plan_trip") {
        html += _buildPlanCard(result);
      } else if (tr.name === "regret_calculate") {
        html += _buildRegretCard(result);
      }
    }
    return html;
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
      const res = await API.agent(text, _chatHistory);
      removeTyping();
      if (!res || typeof res !== "object") {
        addBubble("bot", "抱歉，收到了異常的回應格式。");
      } else {
        // 更新 chat history
        if (res.history) {
          _chatHistory = res.history;
          if (_chatHistory.length > _MAX_HISTORY) {
            _chatHistory = _chatHistory.slice(-_MAX_HISTORY);
          }
        }

        const replyHtml = formatReply(res.reply || "抱歉，我無法理解你的問題。");
        const extraHtml = buildToolCards(res.tool_results);
        addBubble("bot", replyHtml + extraHtml);
      }
    } catch (err) {
      removeTyping();
      addBubble("bot", "抱歉，發生了一點問題，請稍後再試。");
    } finally {
      _sending = false;
      sendBtn.disabled = false;
      agentInput.focus();
    }
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

  HomePage.destroy = () => {
    if (pageContainer) pageContainer.classList.remove("is-agent-page");
    _chatHistory = [];
  };
};

// ── 精算結果卡片渲染 ──
function _buildInstantCard(data) {
  const results = data.results || [];
  if (!results.length) return "";
  const best = results[0];
  const rtype = best.reward_type || "cashback";
  const unit = rtype === "cashback" ? "回饋" : (rtype === "miles" ? "哩程" : "點");

  let html = `<div class="agent-data-card">`;
  html += `<div class="agent-data-best">
    <div class="agent-data-best-label">💳 你的最佳卡</div>
    <div class="agent-data-best-name">${escapeHtml(best.bank_name)} ${escapeHtml(best.card_name)}</div>
    <div class="agent-data-best-reward">$${(best.actual_reward || 0).toFixed(1)} <small>${unit}</small></div>
    <div class="agent-data-best-rate">${best.reward_rate}%</div>
  </div>`;

  if (results.length > 1) {
    html += `<div class="agent-data-others">`;
    results.slice(1, 4).forEach((r, i) => {
      html += `<div class="agent-data-other">
        <span class="agent-data-rank">#${i + 2}</span>
        <span class="agent-data-other-name">${escapeHtml(r.bank_name)} ${escapeHtml(r.card_name)}</span>
        <span class="agent-data-other-reward">$${(r.actual_reward || 0).toFixed(1)}</span>
      </div>`;
    });
    html += `</div>`;
  }

  const bc = data.better_card;
  if (bc) {
    const bcType = bc.reward_type || "cashback";
    const bcUnit = bcType === "cashback" ? "回饋" : (bcType === "miles" ? "哩程" : "點");
    html += `<div class="agent-data-upgrade">
      <div class="agent-data-upgrade-label">✨ 辦卡推薦</div>
      <div class="agent-data-upgrade-name">${escapeHtml(bc.bank_name)} ${escapeHtml(bc.card_name)}</div>
      <div class="agent-data-upgrade-detail">${bc.reward_rate}% → $${(bc.actual_reward || 0).toFixed(1)} ${bcUnit}，多賺 $${(bc.extra_reward || 0).toFixed(1)}</div>
    </div>`;
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
      html += `<div class="agent-data-bring-item">${escapeHtml(c.card)} → ${escapeHtml(usage)}</div>`;
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
