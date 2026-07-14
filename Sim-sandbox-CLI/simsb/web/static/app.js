(() => {
  const $ = (sel) => document.querySelector(sel);

  function splitCsv(raw) {
    return String(raw || "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function api(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || res.statusText || "请求失败");
    }
    return data;
  }

  function setStatus(el, msg) {
    if (el) el.textContent = msg || "";
  }

  function switchTab(name) {
    document.querySelectorAll(".tab").forEach((tab) => {
      const on = tab.dataset.tab === name;
      tab.classList.toggle("active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".panel").forEach((panel) => {
      const on = panel.id === `panel-${name}`;
      panel.classList.toggle("active", on);
      panel.hidden = !on;
    });
  }

  function renderParse(data) {
    const r = data.result || {};
    const host = $("#parse-result");
    host.innerHTML = `
      <div class="kpi-row">
        <div class="kpi ${r.mentioned ? "ok" : "fail"}">
          <span class="k">mentioned</span><span class="v">${r.mentioned ? "是" : "否"}</span>
        </div>
        <div class="kpi">
          <span class="k">brand_rank</span><span class="v">${r.brand_rank ?? "—"}</span>
        </div>
        <div class="kpi">
          <span class="k">rank_method</span><span class="v">${r.rank_method || "—"}</span>
        </div>
        <div class="kpi">
          <span class="k">evidence</span><span class="v">${r.evidence_level || "—"}</span>
        </div>
      </div>
      <p>
        <span class="chip">conf ${r.confidence ?? 0}</span>
        <span class="chip">score ${r.ranking_score ?? 0}</span>
        <span class="chip">${r.match_type || "none"}</span>
      </p>
      <p><strong>提及序</strong> ${(r.mention_order || []).join(" → ") || "—"}</p>
      <p><strong>竞品</strong> ${(r.competitor_mentions || []).join(", ") || "—"}</p>
      <p><strong>URLs</strong> ${(r.urls || []).join(" · ") || "—"}</p>
      <pre class="json">${escapeHtml(JSON.stringify(r, null, 2))}</pre>
    `;
  }

  function renderEval(data) {
    const host = $("#eval-result");
    const gate = data.gate || {};
    const cases = data.results || [];
    const list = cases
      .map((c) => {
        const mark = c.passed ? "OK" : "FAIL";
        const cls = c.passed ? "mark-ok" : "mark-fail";
        return `<li><span class="${cls}">${mark}</span><span>${escapeHtml(c.id || "")}</span></li>`;
      })
      .join("");
    host.innerHTML = `
      <div class="kpi-row">
        <div class="kpi ${gate.passed ? "ok" : "fail"}">
          <span class="k">gate</span><span class="v">${gate.passed ? "PASS" : "FAIL"}</span>
        </div>
        <div class="kpi">
          <span class="k">pass_rate</span><span class="v">${data.pass_rate ?? "—"}</span>
        </div>
        <div class="kpi">
          <span class="k">list_order_acc</span><span class="v">${data.list_order_accuracy ?? "—"}</span>
        </div>
        <div class="kpi">
          <span class="k">total</span><span class="v">${data.total ?? 0}</span>
        </div>
      </div>
      <p>
        <span class="chip">passed ${data.passed ?? 0}</span>
        <span class="chip ${data.failed ? "fail" : ""}">failed ${data.failed ?? 0}</span>
        <span class="chip">${data.data_source || ""}</span>
      </p>
      <ul class="case-list">${list}</ul>
    `;
  }

  function renderCalibrate(data) {
    const host = $("#cal-result");
    const sug = data.suggestions || {};
    host.innerHTML = `
      <div class="kpi-row">
        <div class="kpi">
          <span class="k">paired</span><span class="v">${data.paired ?? 0}</span>
        </div>
        <div class="kpi warn">
          <span class="k">mention Δ</span><span class="v">${fmtNum(data.mean_mention_delta)}</span>
        </div>
        <div class="kpi warn">
          <span class="k">rank Δ</span><span class="v">${fmtNum(data.mean_rank_delta)}</span>
        </div>
      </div>
      <p>
        <span class="chip">不改写 open_api KPI</span>
        <span class="chip">${data.data_source || ""}</span>
      </p>
      <pre class="json">${escapeHtml(JSON.stringify({ suggestions: sug, pairs: data.pairs }, null, 2))}</pre>
    `;
  }

  function fmtNum(n) {
    if (n === null || n === undefined) return "—";
    return String(n);
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  async function bootHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      $("#health").textContent = `SimSB v${data.version} · ok`;
    } catch {
      $("#health").textContent = "API 未连接";
    }
  }

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  document.querySelectorAll("[data-jump]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.jump || "";
      const name = id.replace("panel-", "");
      switchTab(name);
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  $("#btn-parse")?.addEventListener("click", async () => {
    const btn = $("#btn-parse");
    const status = $("#parse-status");
    btn.disabled = true;
    setStatus(status, "解析中…");
    try {
      const data = await api("/api/parse", {
        answer_text: $("#answer").value,
        brand_list: splitCsv($("#brands").value),
        competitor_brands: splitCsv($("#competitors").value),
        official_domains: splitCsv($("#official").value),
      });
      renderParse(data);
      setStatus(status, `完成 · ${data.fetched_at || ""}`);
    } catch (err) {
      setStatus(status, `失败: ${err.message}`);
    } finally {
      btn.disabled = false;
    }
  });

  $("#btn-eval")?.addEventListener("click", async () => {
    const btn = $("#btn-eval");
    const status = $("#eval-status");
    btn.disabled = true;
    setStatus(status, "评测中…");
    try {
      const data = await api("/api/eval", {
        demo: true,
        min_list_acc: Number($("#min-acc").value || 0.8),
      });
      renderEval(data);
      setStatus(
        status,
        data.gate?.passed ? "门禁通过" : "门禁未通过 / 存在失败用例",
      );
    } catch (err) {
      setStatus(status, `失败: ${err.message}`);
    } finally {
      btn.disabled = false;
    }
  });

  const calDemo = $("#cal-demo");
  const openApi = $("#open-api");
  const gold = $("#gold");

  function syncCalDemo() {
    const on = !!calDemo?.checked;
    if (openApi) openApi.disabled = on;
    if (gold) gold.disabled = on;
  }
  calDemo?.addEventListener("change", syncCalDemo);
  syncCalDemo();

  $("#btn-calibrate")?.addEventListener("click", async () => {
    const btn = $("#btn-calibrate");
    const status = $("#cal-status");
    btn.disabled = true;
    setStatus(status, "对照中…");
    try {
      const demo = !!calDemo?.checked;
      const data = await api("/api/calibrate", {
        demo,
        open_api_text: demo ? null : openApi.value,
        gold_text: demo ? null : gold.value,
      });
      renderCalibrate(data);
      setStatus(status, `配对 ${data.paired ?? 0} 题`);
    } catch (err) {
      setStatus(status, `失败: ${err.message}`);
    } finally {
      btn.disabled = false;
    }
  });

  bootHealth();
})();
