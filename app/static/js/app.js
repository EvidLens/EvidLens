/* EvidLens - Client JS - v2.0.0
 * RULE: NEVER redirect to /auth/login from JS.
 * All 6 client pages are PUBLIC. Server enforces auth only on
 * Generate / Download / Billing. 401 = show Trial / public view.
 */
(function(){
  'use strict';

  const EvidLens = {};
  window.EvidLens = EvidLens;
  window.app = EvidLens;

  // ---------- Helpers ----------
  EvidLens.getToken = function(){
    try { return localStorage.getItem('token') || ''; } catch(e){ return ''; }
  };
  EvidLens.setToken = function(t){
    try { if(t) localStorage.setItem('token', t); else localStorage.removeItem('token'); } catch(e){}
  };
  EvidLens.getCookie = function(name){
    const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  };
  EvidLens.isLoggedIn = function(){
    return !!(EvidLens.getToken() || EvidLens.getCookie('user_id') || EvidLens.getCookie('access_token'));
  };
  EvidLens.formatNumber = function(n){
    if(n == null || isNaN(n)) return '—';
    return Number(n).toLocaleString('en-KE');
  };
  EvidLens.formatMoney = function(n){
    if(n == null || isNaN(n)) return '—';
    return 'KES ' + Number(n).toLocaleString('en-KE');
  };
  EvidLens.formatDate = function(d){
    if(!d) return '—';
    try { return new Date(d).toLocaleDateString('en-KE', {year:'numeric', month:'short', day:'numeric'}); }
    catch(e){ return String(d); }
  };
  EvidLens.escape = function(s){
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  };

  // ---------- Toast ----------
  EvidLens.toast = function(msg, type){
    let el = document.getElementById('global-toast');
    if(!el){
      el = document.createElement('div');
      el.id = 'global-toast';
      el.className = 'fixed top-20 right-4 z-[100] bg-[#0A1F44] text-white px-4 py-3 rounded-lg shadow-lg max-w-xs text-sm';
      document.body.appendChild(el);
    }
    el.style.display = 'block';
    el.style.background = type === 'error' ? '#DC2626' : type === 'success' ? '#059669' : '#0A1F44';
    el.innerText = msg;
    clearTimeout(el._t);
    el._t = setTimeout(()=>{ el.style.display = 'none'; }, 4000);
  };

  // ---------- API - NEVER redirects ----------
  EvidLens.api = async function(url, options){
    options = options || {};
    const headers = Object.assign({'Content-Type': 'application/json'}, options.headers || {});
    const token = EvidLens.getToken();
    if(token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(url, Object.assign({}, options, {headers, credentials: 'same-origin'}));
    // 401 = NOT LOGGED IN -> return response, let caller show Trial / public view
    // Do NOT window.location to login. Ever.
    if(res.status === 401){
      console.log('[EvidLens] 401 on', url, '- showing public view, not redirecting');
    }
    return res;
  };

  EvidLens.apiJSON = async function(url, options){
    const r = await EvidLens.api(url, options);
    const data = await r.json().catch(()=>({}));
    return {ok: r.ok, status: r.status, data: data};
  };

  // Legacy global fetch wrapper for pages that use fetch() directly
  // We do NOT override window.fetch - that breaks other libs. Pages should use EvidLens.api().

  // ---------- Auth actions ----------
  EvidLens.requireLogin = function(actionName){
    // Called ONLY when user clicks Generate / Download / Pay - not on page load
    if(!EvidLens.isLoggedIn()){
      EvidLens.toast('Please login to ' + (actionName || 'continue') + ' — or continue browsing as Trial.', 'error');
      // Give user choice, don't force redirect
      setTimeout(()=>{ if(confirm('Login to ' + (actionName || 'continue') + '?')) window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname); }, 300);
      return false;
    }
    return true;
  };

  EvidLens.logout = function(){
    EvidLens.setToken('');
    window.location.href = '/auth/logout';
  };

  // ---------- Meta loaders (used by all 6 pages) ----------
  EvidLens.loadSectors = async function(selectEl){
    if(!selectEl) return [];
    try{
      const {ok, data} = await EvidLens.apiJSON('/api/meta/sectors');
      const list = (data.sectors || data || []);
      selectEl.innerHTML = '<option value="">All Sectors</option>' + list.map(s=>{
        const name = typeof s === 'string' ? s : (s.name || s.sector || s);
        return `<option value="${EvidLens.escape(name)}">${EvidLens.escape(name)}</option>`;
      }).join('');
      return list;
    }catch(e){ console.log('sectors fail', e); return []; }
  };

  EvidLens.loadCounties = async function(selectEl){
    if(!selectEl) return [];
    try{
      const {ok, data} = await EvidLens.apiJSON('/api/meta/counties');
      const list = (data.counties || data || []);
      selectEl.innerHTML = '<option value="">All Counties</option>' + list.map(c=>{
        const name = typeof c === 'string' ? c : (c.name || c.county || c);
        return `<option value="${EvidLens.escape(name)}">${EvidLens.escape(name)}</option>`;
      }).join('');
      return list;
    }catch(e){ console.log('counties fail', e); return []; }
  };

  EvidLens.loadSubcounties = async function(county, selectEl){
    if(!selectEl) return [];
    if(!county){ selectEl.innerHTML = '<option value="">All Subcounties</option>'; return []; }
    try{
      const {ok, data} = await EvidLens.apiJSON('/api/meta/subcounties?county=' + encodeURIComponent(county));
      const list = (data.subcounties || data.sub_counties || data || []);
      selectEl.innerHTML = '<option value="">All Subcounties</option>' + list.map(s=>{
        const name = typeof s === 'string' ? s : (s.name || s.subcounty || s);
        return `<option value="${EvidLens.escape(name)}">${EvidLens.escape(name)}</option>`;
      }).join('');
      return list;
    }catch(e){ console.log('subcounties fail', e); return []; }
  };

  // ---------- Prices table (Demand / Market pages) ----------
  EvidLens.loadPrices = async function(params, containerId){
    const el = document.getElementById(containerId || 'prices-container');
    if(el) el.innerHTML = '<p class="text-gray-500 text-sm py-4">Loading prices...</p>';
    try{
      const q = new URLSearchParams(params || {search:'', page:1, limit:15, sort_by:'id', order:'desc'});
      const {ok, data} = await EvidLens.apiJSON('/api/data/prices?' + q.toString());
      const rows = data.prices || data.items || data || [];
      if(!el) return rows;
      if(!rows.length){ el.innerHTML = '<p class="text-gray-500 text-sm py-4">No prices found. Try another search.</p>'; return rows; }
      el.innerHTML = rows.map(r=>`
        <div class="flex justify-between items-center border-b py-2 text-sm">
          <div><div class="font-bold">${EvidLens.escape(r.product || r.name || 'Product')}</div><div class="text-gray-500 text-xs">${EvidLens.escape(r.county || '')} ${r.subcounty ? '• ' + EvidLens.escape(r.subcounty) : ''} • ${EvidLens.escape(r.market || r.retail_outlet || '')}</div></div>
          <div class="font-bold text-[#0A1F44]">${EvidLens.formatMoney(r.price || r.price_kes)}</div>
        </div>`).join('');
      return rows;
    }catch(e){
      if(el) el.innerHTML = '<p class="text-red-500 text-sm py-4">Failed to load prices. Refresh page.</p>';
      return [];
    }
  };

  // ---------- Analyze (Competitive / Demand) - handles 422 properly ----------
  EvidLens.analyze = async function(payload, resultContainerId){
    const el = resultContainerId ? document.getElementById(resultContainerId) : null;
    if(el) el.innerHTML = '<p class="text-gray-500 text-sm py-4">Analyzing...</p>';
    // Clean payload: drop empty strings so backend never gets 422 for empty county/sector
    const clean = {};
    Object.keys(payload || {}).forEach(k=>{
      const v = payload[k];
      if(v !== '' && v !== null && v !== undefined) clean[k] = v;
    });
    try{
      const r = await EvidLens.api('/api/analyze', {method:'POST', body: JSON.stringify(clean)});
      const data = await r.json().catch(()=>({}));
      if(r.status === 422){
        const msg = (data.detail && data.detail[0] && data.detail[0].msg) ? data.detail[0].msg : 'Please fill County and Sector, then try again.';
        if(el) el.innerHTML = `<p class="text-red-600 text-sm py-4">⚠️ ${EvidLens.escape(msg)} — pick a County + Sector and click Analyze again.</p>`;
        EvidLens.toast(msg, 'error');
        return {ok:false, data};
      }
      if(!r.ok){
        if(el) el.innerHTML = `<p class="text-red-600 text-sm py-4">Analysis failed (${r.status}). Try again.</p>`;
        return {ok:false, data};
      }
      if(el){
        el.innerHTML = `<div class="bg-white rounded-lg border p-4 text-sm whitespace-pre-wrap">${EvidLens.escape(JSON.stringify(data, null, 2))}</div>`;
      }
      return {ok:true, data};
    }catch(e){
      if(el) el.innerHTML = '<p class="text-red-600 text-sm py-4">Network error. Check connection and try again.</p>';
      return {ok:false, error:String(e)};
    }
  };

  // ---------- Reports - poll until READY, never stuck ----------
  EvidLens.generateReport = async function(payload, onUpdate){
    try{
      const r = await EvidLens.api('/reports/generate', {method:'POST', body: JSON.stringify(payload || {})});
      const data = await r.json().catch(()=>({}));
      if(r.status === 402){ EvidLens.toast('Report Builder is Pro only. Upgrade to Pro KES 5,000.', 'error'); return {ok:false, status:402, data}; }
      if(!r.ok){ EvidLens.toast(data.detail || 'Report generation failed', 'error'); return {ok:false, status:r.status, data}; }
      const id = data.report_id;
      if(onUpdate) onUpdate({status:'generating', report_id:id});
      // Poll every 5s, max 3 minutes
      for(let i=0;i<36;i++){
        await new Promise(res=>setTimeout(res, 5000));
        const st = await EvidLens.apiJSON('/reports/status/' + id);
        const s = String(st.data.status || '').toUpperCase();
        if(onUpdate) onUpdate({status:s, report_id:id, data:st.data});
        if(s.includes('READY')){ EvidLens.toast('Report ready! Click Download.', 'success'); return {ok:true, report_id:id, data:st.data}; }
        if(s.includes('FAIL')){ EvidLens.toast('Report failed: ' + (st.data.error || 'Generator error'), 'error'); return {ok:false, report_id:id, data:st.data}; }
      }
      EvidLens.toast('Still generating - check Reports List in a minute.', 'error');
      return {ok:false, report_id:id, timeout:true};
    }catch(e){ EvidLens.toast('Network error generating report', 'error'); return {ok:false, error:String(e)}; }
  };

  EvidLens.downloadReport = async function(reportId){
    if(!reportId) return;
    // Don't fetch as blob - let browser download directly, shows real error if not ready
    window.location.href = '/reports/download/' + reportId;
  };

  // ---------- Auto-wire common page elements ----------
  document.addEventListener('DOMContentLoaded', function(){
    // County -> Subcounty cascading
    const countySel = document.querySelector('[data-county-select]');
    const subcountySel = document.querySelector('[data-subcounty-select]');
    if(countySel && subcountySel){
      countySel.addEventListener('change', ()=> EvidLens.loadSubcounties(countySel.value, subcountySel));
    }
    // Any [data-load-sectors] / [data-load-counties] selects
    document.querySelectorAll('[data-load-sectors]').forEach(el=> EvidLens.loadSectors(el));
    document.querySelectorAll('[data-load-counties]').forEach(el=> EvidLens.loadCounties(el));

    // Global search forms: [data-prices-form]
    document.querySelectorAll('[data-prices-form]').forEach(form=>{
      form.addEventListener('submit', function(e){
        e.preventDefault();
        const fd = new FormData(form);
        EvidLens.loadPrices({search: fd.get('search')||'', page:1, limit:15, sort_by:'id', order:'desc'}, form.getAttribute('data-target') || 'prices-container');
      });
    });

    // Analyze forms: [data-analyze-form]
    document.querySelectorAll('[data-analyze-form]').forEach(form=>{
      form.addEventListener('submit', function(e){
        e.preventDefault();
        const fd = new FormData(form);
        const payload = {};
        fd.forEach((v,k)=> payload[k]=v);
        EvidLens.analyze(payload, form.getAttribute('data-target') || 'analyze-result');
      });
    });

    // Report generate forms: [data-report-form]
    document.querySelectorAll('[data-report-form]').forEach(form=>{
      form.addEventListener('submit', async function(e){
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        const old = btn ? btn.innerText : '';
        if(btn){ btn.disabled = true; btn.innerText = 'Generating...'; }
        const fd = new FormData(form);
        const payload = {};
        fd.forEach((v,k)=> payload[k]=v);
        const res = await EvidLens.generateReport(payload, (u)=>{
          if(btn) btn.innerText = 'Generating... (' + u.status + ')';
        });
        if(btn){ btn.disabled = false; btn.innerText = old || 'Generate Report'; }
        if(res.ok){
          const dl = document.getElementById('download-btn');
          if(dl){ dl.href = '/reports/download/' + res.report_id; dl.classList.remove('hidden'); }
        }
      });
    });

    // Download buttons: [data-download-report="id"]
    document.querySelectorAll('[data-download-report]').forEach(btn=>{
      btn.addEventListener('click', ()=> EvidLens.downloadReport(btn.getAttribute('data-download-report')));
    });
  });

})();
