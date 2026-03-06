/**
 * my-cards.js — 選卡頁：按銀行分組 checkbox
 */
async function MyCardsPage() {
  const cards = await API.getCards();

  // group by bank
  const groups = {};
  cards.forEach((c) => {
    if (!groups[c.bank_name]) groups[c.bank_name] = [];
    groups[c.bank_name].push(c);
  });

  const myIds = Store.getMyCards();

  const banksHtml = Object.entries(groups)
    .map(
      ([bank, bankCards]) => `
      <div class="bank-group">
        <div class="bank-name">${bank}</div>
        ${bankCards
          .map(
            (c) => `
          <label class="card-check-item">
            <input type="checkbox" data-card-id="${c.id}" ${myIds.includes(c.id) ? "checked" : ""}>
            <div class="card-check-info">
              <div class="card-check-name">${c.card_name}</div>
              <div class="card-check-note">${c.note || ""}</div>
            </div>
            <span class="card-check-fee">${c.annual_fee ? `$${c.annual_fee}/年` : "免年費"}</span>
          </label>`
          )
          .join("")}
      </div>`
    )
    .join("");

  return `
    <div class="selected-count" id="selectedCount">已選 ${myIds.length} 張卡</div>
    ${banksHtml}
  `;
}

MyCardsPage.init = () => {
  const countEl = document.getElementById("selectedCount");

  document.querySelectorAll('input[data-card-id]').forEach((cb) => {
    cb.addEventListener("change", () => {
      const cardId = parseInt(cb.dataset.cardId, 10);
      const ids = Store.toggleCard(cardId);
      countEl.textContent = `已選 ${ids.length} 張卡`;
    });
  });
};
