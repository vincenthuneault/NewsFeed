/* Interface de développement NewsFeed */

(async () => {

  // ── Helpers sécurité ──────────────────────────────────
  function esc(str) {
    if (!str && str !== 0) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── API ───────────────────────────────────────────────
  async function api(url) {
    const res = await fetch(url).catch(() => null);
    if (!res) return null;
    if (res.status === 401) { location.href = '/'; return null; }
    return res.json().catch(() => null);
  }

  // ── Formatage ─────────────────────────────────────────
  function fmtDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('fr-CA') + ' ' +
           d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' });
  }

  function trunc(str, max = 80) {
    if (!str) return '—';
    return str.length > max ? str.slice(0, max) + '…' : str;
  }

  function badge(status) {
    const cls = { success: 'badge-success', failed: 'badge-danger', partial: 'badge-warning' };
    return `<span class="badge ${cls[status] || 'badge-neutral'}">${esc(status)}</span>`;
  }

  // ── Modal ─────────────────────────────────────────────
  const modal       = document.getElementById('modal');
  const modalTitle  = document.getElementById('modal-title');
  const modalBodyEl = document.getElementById('modal-body');

  function openModal(title, content) {
    modalTitle.textContent = title;
    modalBodyEl.textContent = typeof content === 'string'
      ? content
      : JSON.stringify(content, null, 2);
    modal.classList.remove('hidden');
  }

  function closeModal() { modal.classList.add('hidden'); }

  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-backdrop').addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // ── Pagination ────────────────────────────────────────
  function renderPager(containerId, page, total, perPage, onPage) {
    const el = document.getElementById(containerId);
    const totalPages = Math.ceil(total / perPage);
    if (totalPages <= 1) { el.innerHTML = ''; return; }

    let start = Math.max(1, page - 2);
    let end   = Math.min(totalPages, start + 4);
    start     = Math.max(1, end - 4);

    let html = `<button class="page-btn" data-p="${page - 1}" ${page <= 1 ? 'disabled' : ''}>‹</button>`;
    for (let p = start; p <= end; p++) {
      html += `<button class="page-btn ${p === page ? 'active' : ''}" data-p="${p}">${p}</button>`;
    }
    html += `<button class="page-btn" data-p="${page + 1}" ${page >= totalPages ? 'disabled' : ''}>›</button>`;
    html += `<span class="page-info">${total.toLocaleString('fr-CA')} résultat${total !== 1 ? 's' : ''}</span>`;

    el.innerHTML = html;
    el.querySelectorAll('.page-btn:not([disabled])').forEach(btn =>
      btn.addEventListener('click', () => onPage(+btn.dataset.p))
    );
  }

  // ── Navigation onglets ────────────────────────────────
  const tabLoaded = {};
  const tabBtns   = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');

  function activateTab(name) {
    tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    tabPanels.forEach(p => p.classList.toggle('hidden', p.id !== `tab-${name}`));
    if (!tabLoaded[name]) loadTab(name);
  }

  tabBtns.forEach(btn => btn.addEventListener('click', () => activateTab(btn.dataset.tab)));

  // ── Tableau de bord ───────────────────────────────────
  async function loadDashboard() {
    const d = await api('/api/dev/stats');
    if (!d) return;

    document.getElementById('stat-news-val').textContent      = d.news_items.total.toLocaleString('fr-CA');

    document.getElementById('stat-comments-val').textContent  = d.comments.total.toLocaleString('fr-CA');
    document.getElementById('stat-comments-sub').textContent  = `+${d.comments.this_week} cette semaine`;

    document.getElementById('stat-bugs-val').textContent      = d.bugs.total.toLocaleString('fr-CA');
    document.getElementById('stat-bugs-sub').textContent      = `+${d.bugs.this_week} cette semaine`;

    document.getElementById('stat-fb-val').textContent        = d.feedbacks.total.toLocaleString('fr-CA');
    document.getElementById('stat-fb-sub').textContent        =
      `👍 ${d.feedbacks.likes} · 👎 ${d.feedbacks.dislikes} · ⏭ ${d.feedbacks.skips}`;

    const rate = (d.agent_runs.success_rate * 100).toFixed(0);
    document.getElementById('stat-agents-val').textContent    = `${rate} %`;
    document.getElementById('stat-agents-sub').textContent    =
      d.agent_runs.last_run ? `Dernier run : ${fmtDate(d.agent_runs.last_run)}` : 'Aucun run';

    tabLoaded.dashboard = true;
  }

  // ── Commentaires ──────────────────────────────────────
  let commentsPage = 1;
  let commentsQ    = '';

  async function loadComments() {
    const tbody = document.getElementById('comments-body');
    tbody.innerHTML = `<tr class="loading-row"><td colspan="5">Chargement…</td></tr>`;

    const p = new URLSearchParams({ page: commentsPage, per_page: 20, q: commentsQ });
    const d = await api(`/api/dev/comments?${p}`);
    if (!d) return;

    if (!d.items.length) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="5">Aucun commentaire</td></tr>`;
    } else {
      tbody.innerHTML = d.items.map(c => {
        const shortBody = trunc(c.body, 80);
        const hasMore   = c.body.length > 80;
        return `<tr>
          <td class="cell-id">${c.id}</td>
          <td>
            <span class="truncate" style="max-width:260px">${esc(shortBody)}</span>
            ${hasMore ? `<button class="btn-detail" data-body="${esc(c.body)}" data-title="Commentaire #${c.id}">Voir</button>` : ''}
          </td>
          <td><span class="truncate" style="max-width:200px" title="${esc(c.news_item.title)}">${esc(c.news_item.title)}</span></td>
          <td class="cell-id">${esc(c.news_item.source_name)}</td>
          <td class="cell-id">${fmtDate(c.created_at)}</td>
        </tr>`;
      }).join('');

      tbody.querySelectorAll('.btn-detail').forEach(btn =>
        btn.addEventListener('click', () => openModal(btn.dataset.title, btn.dataset.body))
      );
    }

    renderPager('comments-pager', commentsPage, d.total, 20, p => { commentsPage = p; loadComments(); });
    tabLoaded.comments = true;
  }

  let commentsTimer;
  document.getElementById('comments-search').addEventListener('input', e => {
    clearTimeout(commentsTimer);
    commentsTimer = setTimeout(() => { commentsQ = e.target.value; commentsPage = 1; loadComments(); }, 300);
  });

  // ── Rapports de bug ───────────────────────────────────
  let bugsPage = 1;

  async function loadBugs() {
    const tbody = document.getElementById('bugs-body');
    tbody.innerHTML = `<tr class="loading-row"><td colspan="5">Chargement…</td></tr>`;

    const p = new URLSearchParams({ page: bugsPage, per_page: 20 });
    const d = await api(`/api/dev/bugs?${p}`);
    if (!d) return;

    if (!d.items.length) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="5">Aucun rapport de bug</td></tr>`;
    } else {
      // On conserve les données pour le modal (data-* ne peut pas stocker du JSON complexe fiablement)
      const bugsById = Object.fromEntries(d.items.map(b => [b.id, b]));

      tbody.innerHTML = d.items.map(b => {
        const ctx         = b.context;
        const activeArt   = ctx?.active_article ? trunc(ctx.active_article, 40) : '—';
        return `<tr>
          <td class="cell-id">${b.id}</td>
          <td>
            <span class="truncate" style="max-width:300px">${esc(trunc(b.description, 100))}</span>
            <button class="btn-detail btn-bug-full" data-id="${b.id}">Voir</button>
          </td>
          <td class="cell-id">${esc(activeArt)}</td>
          <td class="cell-id">${fmtDate(b.created_at)}</td>
          <td>${ctx ? `<button class="btn-detail btn-bug-ctx" data-id="${b.id}">JSON</button>` : '—'}</td>
        </tr>`;
      }).join('');

      tbody.querySelectorAll('.btn-bug-full').forEach(btn => {
        const b = bugsById[btn.dataset.id];
        btn.addEventListener('click', () =>
          openModal(`Bug #${b.id}`, b.description +
            (b.context ? '\n\n─── Contexte ───\n' + JSON.stringify(b.context, null, 2) : ''))
        );
      });
      tbody.querySelectorAll('.btn-bug-ctx').forEach(btn => {
        const b = bugsById[btn.dataset.id];
        btn.addEventListener('click', () => openModal(`Contexte — Bug #${b.id}`, b.context));
      });
    }

    renderPager('bugs-pager', bugsPage, d.total, 20, p => { bugsPage = p; loadBugs(); });
    tabLoaded.bugs = true;
  }

  // ── Agents ────────────────────────────────────────────
  let agentsPage   = 1;
  let agentFilter  = '';
  let agentNamesPopulated = false;

  async function loadAgents() {
    const tbody = document.getElementById('agents-body');
    tbody.innerHTML = `<tr class="loading-row"><td colspan="7">Chargement…</td></tr>`;

    const p = new URLSearchParams({ page: agentsPage, per_page: 50, agent: agentFilter });
    const d = await api(`/api/dev/agent-runs?${p}`);
    if (!d) return;

    // Peupler le select au premier appel
    if (!agentNamesPopulated && d.agent_names?.length) {
      const sel = document.getElementById('agent-filter');
      d.agent_names.forEach(name => {
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name;
        sel.appendChild(opt);
      });
      agentNamesPopulated = true;
    }

    if (!d.items.length) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Aucune exécution</td></tr>`;
    } else {
      tbody.innerHTML = d.items.map(r => `<tr>
        <td class="cell-id">${r.id}</td>
        <td>${esc(r.agent_name)}</td>
        <td>${badge(r.status)}</td>
        <td class="cell-id">${r.items_collected}</td>
        <td class="cell-id">${r.duration_seconds} s</td>
        <td class="cell-id">${r.error_message ? `<span title="${esc(r.error_message)}">${esc(trunc(r.error_message, 50))}</span>` : '—'}</td>
        <td class="cell-id">${fmtDate(r.created_at)}</td>
      </tr>`).join('');
    }

    renderPager('agents-pager', agentsPage, d.total, 50, p => { agentsPage = p; loadAgents(); });
    tabLoaded.agents = true;
  }

  document.getElementById('agent-filter').addEventListener('change', e => {
    agentFilter = e.target.value; agentsPage = 1; loadAgents();
  });

  // ── Articles ──────────────────────────────────────────
  const CATEGORIES = {
    youtube_subs:     'Mes abonnements YouTube',
    youtube_trending: 'Tendances YouTube',
    viral:            'Contenu viral',
    tech_ai:          'Tech & IA',
    politique_intl:   'Politique internationale',
    politique_ca:     'Politique canadienne',
    politique_qc:     'Politique québécoise',
    evenements_mtl:   'Événements Montréal',
    musique_electro:  'Musique électronique',
    humour:           'Humour',
    local_contrecoeur:'Contrecoeur & Sorel',
    local_alerte:     'Alertes locales',
    vehicules_ev:     'Véhicules électriques & autonomes',
    spatial:          'Espace & exploration',
  };

  // Peupler le select catégories
  const catSel = document.getElementById('category-filter');
  Object.entries(CATEGORIES).forEach(([k, v]) => {
    const opt = document.createElement('option');
    opt.value = k; opt.textContent = v;
    catSel.appendChild(opt);
  });

  let newsPage     = 1;
  let newsQ        = '';
  let newsCategory = '';

  async function loadNews() {
    const tbody = document.getElementById('news-body');
    tbody.innerHTML = `<tr class="loading-row"><td colspan="8">Chargement…</td></tr>`;

    const p = new URLSearchParams({ page: newsPage, per_page: 20, q: newsQ, category: newsCategory });
    const d = await api(`/api/dev/news?${p}`);
    if (!d) return;

    if (!d.items.length) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="8">Aucun article</td></tr>`;
    } else {
      tbody.innerHTML = d.items.map(item => {
        const catLabel = CATEGORIES[item.category] || item.category;
        return `<tr>
          <td class="cell-id">${item.id}</td>
          <td>
            <a href="${esc(item.source_url)}" target="_blank" rel="noopener"
               style="color:var(--text);text-decoration:none">
              <span class="truncate" style="max-width:340px" title="${esc(item.title)}">${esc(item.title)}</span>
            </a>
          </td>
          <td class="cell-id">${esc(catLabel)}</td>
          <td class="cell-id">${esc(item.source_name)}</td>
          <td class="cell-id">${item.final_score}</td>
          <td class="cell-id">${item.comments_count || '—'}</td>
          <td class="cell-id">${item.feedbacks_count || '—'}</td>
          <td class="cell-id">${fmtDate(item.published_at)}</td>
        </tr>`;
      }).join('');
    }

    renderPager('news-pager', newsPage, d.total, 20, p => { newsPage = p; loadNews(); });
    tabLoaded.news = true;
  }

  let newsTimer;
  document.getElementById('news-search').addEventListener('input', e => {
    clearTimeout(newsTimer);
    newsTimer = setTimeout(() => { newsQ = e.target.value; newsPage = 1; loadNews(); }, 300);
  });
  catSel.addEventListener('change', e => { newsCategory = e.target.value; newsPage = 1; loadNews(); });

  // ── Chargement par onglet ─────────────────────────────
  function loadTab(name) {
    switch (name) {
      case 'dashboard': loadDashboard(); break;
      case 'comments':  loadComments();  break;
      case 'bugs':      loadBugs();      break;
      case 'agents':    loadAgents();    break;
      case 'news':      loadNews();      break;
    }
  }

  // ── Init ─────────────────────────────────────────────
  loadDashboard();

})();
