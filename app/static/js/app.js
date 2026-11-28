(function () {
  'use strict';

  const EvidLens = {};
  window.EvidLens = EvidLens;
  window.app = EvidLens;

  EvidLens.getToken = function () {
    try { return localStorage.getItem('token') || ''; } catch (e) { return ''; }
  };

  EvidLens.setToken = function (t) {
    try { if (t) localStorage.setItem('token', t); else localStorage.removeItem('token'); } catch (e) {}
  };

  EvidLens.getCookie = function (name) {
    const m = document.cookie.match(new RegExp('(^| )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  };

  EvidLens.isLoggedIn = function () {
    return !!(EvidLens.getToken() || EvidLens.getCookie('user_id') || EvidLens.getCookie('access_token'));
  };

  EvidLens.formatNumber = function (n) {
    if (n == null || isNaN(n)) return '—';
    return Number(n).toLocaleString('en-KE');
  };

  EvidLens.formatMoney = function (n) {
    if (n == null || isNaN(n)) return '—';
    return 'KES ' + Number(n).toLocaleString('en-KE');
  };

  EvidLens.formatDate = function (d) {
    if (!d) return '—';
    try { return new Date(d).toLocaleDateString('en-KE', { year: 'numeric', month: 'short', day: 'numeric' }); }
    catch (e) { return String(d); }
  };

  EvidLens.escape = function (s) {
    return String(s ?? '').replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  };

  EvidLens.toast = function (msg, type) {
    let el = document.getElementById('global-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'global-toast';
      el.className = 'fixed top-20 right-4 z-[100] bg-[#0A1F44] text-white px-4 py-3 rounded-lg shadow-lg max-w-xs text-sm';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.style.display = 'block';
    el.style.background = type === 'error' ? '#DC2626' : type === 'success' ? '#059669' : '#0A1F44';
    el.textContent = msg;
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.style.display = 'none'; }, 4000);
  };

  EvidLens.api = async function (url, options) {
    options = options || {};
    const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    const token = EvidLens.getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const controller = new AbortController();
    const timeoutId = setTimeout(function () { controller.abort(); }, options.timeout || 30000);
    try {
      const res = await fetch(url, Object.assign({}, options, { headers: headers, credentials: 'same-origin', signal: controller.signal }));
      if (res.status === 401) {
        console.log('[EvidLens] 401 on', url, '- showing public view, not redirecting');
      }
      return res;
    } catch (e) {
      if (e && e.name === 'AbortError') {
        throw new Error('Request timed out. Check connection and try again.');
      }
      throw e;
    } finally {
      clearTimeout(timeoutId);
    }
  };

  EvidLens.apiJSON = async function (url, options) {
    const r = await EvidLens.api(url, options);
    const data = await r.json().catch(function () { return {}; });
    return { ok: r.ok, status: r.status, data: data };
  };

  EvidLens.requireLogin = function (actionName) {
    if (!EvidLens.isLoggedIn()) {
      EvidLens.toast('Please login to ' + (actionName || 'continue') + ' — or continue browsing as Trial.', 'error');
      setTimeout(function () {
        if (window.confirm('Login to ' + (actionName || 'continue') + '?')) {
          window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
        }
      }, 300);
      return false;
    }
    return true;
  };

  EvidLens.logout = async function () {
    EvidLens.setToken('');
    try { await fetch('/logout', { method: 'POST', credentials: 'same-origin' }); } catch (e) {}
    window.location.href = '/login?logged_out=1';
  };

  EvidLens.fillSelect = function (selectEl, list, placeholder) {
    if (!selectEl) return [];
    selectEl.innerHTML = '<option value="">' + EvidLens.escape(placeholder) + '</option>' + list.map(function (item) {
      const name = typeof item === 'string' ? item : (item.name || item.sector || item.county || item.subcounty || item);
      return '<option value="' + EvidLens.escape(name) + '">' + EvidLens.escape(name) + '</option>';
    }).join('');
    return list;
  };

  EvidLens.loadSectors = async function (selectEl) {
    if (!selectEl) return [];
    try {
      const res = await EvidLens.apiJSON('/api/meta/sectors');
      const list = (res.data.sectors || res.data || []);
      return EvidLens.fillSelect(selectEl, Array.isArray(list) ? list : [], 'All Sectors');
    } catch (e) { console.log('sectors fail', e); return []; }
  };

  EvidLens.loadCounties = async function (selectEl) {
    if (!selectEl) return [];
    try {
      const res = await EvidLens.apiJSON('/api/meta/counties');
      const list = (res.data.counties || res.data || []);
      return EvidLens.fillSelect(selectEl, Array.isArray(list) ? list : [], 'All Counties');
    } catch (e) { console.log('counties fail', e); return []; }
  };

  EvidLens.loadSubcounties = async function (county, selectEl) {
    if (!selectEl) return [];
    if (!county) { selectEl.innerHTML = '<option value="">All Subcounties</option>'; return []; }
    try {
      const res = await EvidLens.apiJSON('/api/meta/subcounties?county=' + encodeURIComponent(county));
      const list = (res.data.subcounties || res.data.sub_counties || res.data || []);
      return EvidLens.fillSelect(selectEl, Array.isArray(list) ? list : [], 'All Subcounties');
    } catch (e) { console.log('subcounties fail', e); return []; }
  };

  EvidLens.loadPrices = async function (params, containerId) {
    const el = document.getElementById(containerId || 'prices-container');
    if (el) el.innerHTML = '<p class="text-gray-500 text-sm py-4">Loading prices...</p>';
    try {
      const q = new URLSearchParams(params || { search: '', page: 1, limit: 15, sort_by: 'id', order: 'desc' });
      const res = await EvidLens.apiJSON('/api/data/prices?' + q.toString());
      const rows = res.data.prices || res.data.items || (Array.isArray(res.data) ? res.data : []);
      if (!el) return rows;
      if (!rows.length) { el.innerHTML = '<p class="text-gray-500 text-sm py-4">No prices found. Try another search.</p>'; return rows; }
      el.innerHTML = rows.map(function (r) {
        return '<div class="flex justify-between items-center border-b py-2 text-sm">'
          + '<div><div class="font-bold">' + EvidLens.escape(r.product || r.name || 'Product') + '</div>'
          + '<div class="text-gray-500 text-xs">' + EvidLens.escape(r.county || '') + (r.subcounty ? ' • ' + EvidLens.escape(r.subcounty) : '') + ' • ' + EvidLens.escape(r.market || r.retail_outlet || '') + '</div></div>'
          + '<div class="font-bold text-[#0A1F44]">' + EvidLens.formatMoney(r.price || r.price_kes) + '</div></div>';
      }).join('');
      return rows;
    } catch (e) {
      if (el) el.innerHTML = '<p class="text-red-500 text-sm py-4">Failed to load prices. Refresh page.</p>';
      return [];
    }
  };

  EvidLens.analyze = async function (payload, resultContainerId) {
    const el = resultContainerId ? document.getElementById(resultContainerId) : null;
    if (el) el.innerHTML = '<p class="text-gray-500 text-sm py-4">Analyzing...</p>';
    const clean = {};
    Object.keys(payload || {}).forEach(function (k) {
      const v = payload[k];
      if (v !== '' && v !== null && v !== undefined) clean[k] = v;
    });
    try {
      const r = await EvidLens.api('/api/analyze', { method: 'POST', body: JSON.stringify(clean) });
      const data = await r.json().catch(function () { return {}; });
      if (r.status === 401) {
        if (el) el.innerHTML = '<p class="text-gray-600 text-sm py-4">Login to analyze, or continue browsing as Trial.</p>';
        EvidLens.toast('Login to analyze.', 'error');
        return { ok: false, data: data };
      }
      if (r.status === 402) {
        if (el) el.innerHTML = '<p class="text-red-600 text-sm py-4">Out of credits. Buy credits or upgrade to continue.</p>';
        EvidLens.toast('Out of credits. Buy credits or upgrade.', 'error');
        return { ok: false, data: data };
      }
      if (r.status === 422) {
        const detail = data.detail;
        const msg = (Array.isArray(detail) && detail[0] && detail[0].msg) ? detail[0].msg : (typeof detail === 'string' ? detail : 'Please fill County and Sector, then try again.');
        if (el) el.innerHTML = '<p class="text-red-600 text-sm py-4">⚠️ ' + EvidLens.escape(msg) + ' — pick a County + Sector and click Analyze again.</p>';
        EvidLens.toast(msg, 'error');
        return { ok: false, data: data };
      }
      if (!r.ok) {
        if (el) el.innerHTML = '<p class="text-red-600 text-sm py-4">Analysis failed (' + r.status + '). Try again.</p>';
        return { ok: false, data: data };
      }
      if (el) {
        const text = data.summary || data.analysis || data.result || JSON.stringify(data, null, 2);
        el.innerHTML = '<div class="bg-white rounded-lg border p-4 text-sm whitespace-pre-wrap">' + EvidLens.escape(text) + '</div>';
      }
      return { ok: true, data: data };
    } catch (e) {
      if (el) el.innerHTML = '<p class="text-red-600 text-sm py-4">Network error. Check connection and try again.</p>';
      return { ok: false, error: String(e) };
    }
  };

  EvidLens.generateReport = async function (payload, onUpdate) {
    try {
      const r = await EvidLens.api('/reports/generate', { method: 'POST', body: JSON.stringify(payload || {}) });
      const data = await r.json().catch(function () { return {}; });
      if (r.status === 402) { EvidLens.toast('Report Builder is Pro only. Upgrade to Pro KES 1,500/mo.', 'error'); return { ok: false, status: 402, data: data }; }
      if (r.status === 401) { EvidLens.toast('Login to generate a report.', 'error'); return { ok: false, status: 401, data: data }; }
      if (!r.ok) { EvidLens.toast(data.detail || 'Report generation failed', 'error'); return { ok: false, status: r.status, data: data }; }
      const id = data.report_id;
      if (!id) { EvidLens.toast('Report generation failed: no report id.', 'error'); return { ok: false, data: data }; }
      if (onUpdate) onUpdate({ status: 'generating', report_id: id });
      for (let i = 0; i < 36; i++) {
        await new Promise(function (res) { setTimeout(res, 5000); });
        const st = await EvidLens.apiJSON('/reports/status/' + encodeURIComponent(id));
        const s = String(st.data.status || '').toUpperCase();
        if (onUpdate) onUpdate({ status: s, report_id: id, data: st.data });
        if (s.includes('READY')) { EvidLens.toast('Report ready! Click Download.', 'success'); return { ok: true, report_id: id, data: st.data }; }
        if (s.includes('FAIL')) { EvidLens.toast('Report failed: ' + (st.data.error || 'Generator error'), 'error'); return { ok: false, report_id: id, data: st.data }; }
      }
      EvidLens.toast('Still generating - check Reports List in a minute.', 'error');
      return { ok: false, report_id: id, timeout: true };
    } catch (e) { EvidLens.toast('Network error generating report', 'error'); return { ok: false, error: String(e) }; }
  };

  EvidLens.downloadReport = function (reportId) {
    if (!reportId) return;
    window.location.href = '/reports/download/' + encodeURIComponent(reportId);
  };

  // ===== EXPORT NAVIGATOR - PRODUCTION - Real UN Comtrade only, no dummy =====
  EvidLens.exportSearch = async function (q, resultsEl, btn) {
    if (!resultsEl) return [];
    if (!q) { EvidLens.toast('Type a product first', 'error'); return []; }
    const oldText = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Searching...'; }
    resultsEl.innerHTML = '<p class="text-gray-500 text-sm py-4">Loading live from UN Comtrade for: ' + EvidLens.escape(q) + '...</p>';
    try {
      const res = await EvidLens.apiJSON('/market/api/export?q=' + encodeURIComponent(q), { timeout: 60000 });
      const data = res.data || {};
      const rows = data.results || data.data || data.rows || (Array.isArray(data) ? data : []);
      if (!res.ok) {
        resultsEl.innerHTML = '<p class="text-red-600 text-sm py-4">Comtrade failed (' + res.status + '): ' + EvidLens.escape(data.error || data.detail || 'Backend error') + '</p>';
        return [];
      }
      if (!rows.length) {
        resultsEl.innerHTML = '<p class="text-gray-500 text-sm py-4">No live Comtrade records found for: ' + EvidLens.escape(q) + '. Try another product name. No dummy data is shown.</p>';
        return [];
      }
      resultsEl.innerHTML = '<h3 class="font-bold py-2">Live results for ' + EvidLens.escape(q) + ' — ' + rows.length + ' markets</h3>'
        + '<div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr class="text-left border-b-2"><th class="py-2">Market</th><th class="py-2">Year</th><th class="py-2">Trade Value (USD)</th><th class="py-2">Quantity</th></tr></thead><tbody>'
        + rows.map(function (r) {
          const partner = r.partner || r.partnerDesc || r.Partner || '-';
          const value = r.value ?? r.primaryValue ?? r.PrimaryValue ?? r.TradeValue ?? 0;
          const year = r.year || r.period || r.Period || '';
          const qty = r.qty ?? r.quantity ?? r.Quantity ?? r.netWgt ?? null;
          return '<tr class="border-b"><td class="py-2">' + EvidLens.escape(partner) + '</td><td class="py-2">' + EvidLens.escape(year) + '</td><td class="py-2">$' + EvidLens.formatNumber(value) + '</td><td class="py-2">' + (qty == null ? '—' : EvidLens.formatNumber(qty)) + '</td></tr>';
        }).join('')
        + '</tbody></table></div><p class="text-gray-400 text-xs py-2">Source: UN Comtrade live via backend. No preview / dummy data.</p>';
      return rows;
    } catch (e) {
      resultsEl.innerHTML = '<p class="text-red-600 text-sm py-4">Error: ' + EvidLens.escape(String(e.message || e)) + '</p>';
      return [];
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = oldText || 'Search Live →'; }
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    const countySel = document.querySelector('[data-county-select]');
    const subcountySel = document.querySelector('[data-subcounty-select]');
    if (countySel && subcountySel) {
      countySel.addEventListener('change', function () { EvidLens.loadSubcounties(countySel.value, subcountySel); });
    }
    document.querySelectorAll('[data-load-sectors]').forEach(function (el) { EvidLens.loadSectors(el); });
    document.querySelectorAll('[data-load-counties]').forEach(function (el) { EvidLens.loadCounties(el); });

    document.querySelectorAll('[data-prices-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const fd = new FormData(form);
        EvidLens.loadPrices({ search: fd.get('search') || '', page: 1, limit: 15, sort_by: 'id', order: 'desc' }, form.getAttribute('data-target') || 'prices-container');
      });
    });

    document.querySelectorAll('[data-analyze-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const fd = new FormData(form);
        const payload = {};
        fd.forEach(function (v, k) { payload[k] = v; });
        EvidLens.analyze(payload, form.getAttribute('data-target') || 'analyze-result');
      });
    });

    document.querySelectorAll('[data-report-form]').forEach(function (form) {
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        const old = btn ? btn.innerText : '';
        if (btn) { btn.disabled = true; btn.innerText = 'Generating...'; }
        try {
          const fd = new FormData(form);
          const payload = {};
          fd.forEach(function (v, k) { payload[k] = v; });
          const res = await EvidLens.generateReport(payload, function (u) {
            if (btn) btn.innerText = 'Generating... (' + u.status + ')';
          });
          if (res.ok) {
            const dl = document.getElementById('download-btn');
            if (dl) { dl.href = '/reports/download/' + encodeURIComponent(res.report_id); dl.classList.remove('hidden'); }
          }
        } finally {
          if (btn) { btn.disabled = false; btn.innerText = old || 'Generate Report'; }
        }
      });
    });

    document.querySelectorAll('[data-download-report]').forEach(function (btn) {
      btn.addEventListener('click', function () { EvidLens.downloadReport(btn.getAttribute('data-download-report')); });
    });

    // EXPORT NAVIGATOR - bind Search Live button (by text, not ID, so it works with your HTML)
    const exportBtn = [...document.querySelectorAll('button')].find(function (b) { return b.textContent.includes('Search Live'); });
    if (exportBtn) {
      exportBtn.addEventListener('click', function (e) {
        e.preventDefault();
        const input = document.getElementById('exportQuery')
          || document.querySelector('input[placeholder*="Coffee" i], input[placeholder*="product" i]')
          || document.querySelector('input[type="text"], input[type="search"], input:not([type])');
        const q = input ? input.value.trim() : '';
        const resultsEl = document.getElementById('exportResults')
          || [...document.querySelectorAll('div')].find(function (d) { return d.textContent.includes('Search to query'); })
          || document.querySelector('main');
        EvidLens.exportSearch(q, resultsEl, exportBtn);
      });
    }
    // Also support a form with data-export-form
    document.querySelectorAll('[data-export-form]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        const fd = new FormData(form);
        const q = fd.get('q') || fd.get('query') || fd.get('product') || '';
        const resultsEl = document.getElementById('exportResults') || document.querySelector('main');
        EvidLens.exportSearch(String(q).trim(), resultsEl, form.querySelector('button[type="submit"]'));
      });
    });
  });

})();
