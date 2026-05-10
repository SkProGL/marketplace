  (function() {
    const min = new Date();
    min.setTime(min.getTime() + 72 * 60 * 60 * 1000);
    const y = min.getFullYear();
    const m = String(min.getMonth() + 1).padStart(2, '0');
    const d = String(min.getDate()).padStart(2, '0');
    const minDate = `${y}-${m}-${d}`;
    const picker = document.getElementById('best_before');
    picker.min = minDate;
    if (!picker.value || picker.value < minDate) picker.value = minDate;
  })();

  function toggleSeasonFields(allYear) {
    document.getElementById('np-season-fields').style.display = allYear ? 'none' : '';
  }

  function switchTab(tab) {
    document.getElementById('pane-new').style.display   = tab === 'new'   ? '' : 'none';
    document.getElementById('pane-batch').style.display = tab === 'batch' ? '' : 'none';
    document.getElementById('tab-new').classList.toggle('active',   tab === 'new');
    document.getElementById('tab-batch').classList.toggle('active', tab === 'batch');
    if (tab === 'batch') updateSuggestedPrice();
  }

  const npDropzone    = document.getElementById('np-dropzone');
  const npImageInput  = document.getElementById('np-image');
  const npPreview     = document.getElementById('np-preview');
  const npPlaceholder = document.getElementById('np-dz-placeholder');
  const npRevert      = document.getElementById('np-revert');

  function showNpPreview(file) {
    const reader = new FileReader();
    reader.onload = e => {
      npPreview.src = e.target.result;
      npPreview.style.display = 'block';
      npPlaceholder.style.display = 'none';
      npDropzone.style.borderStyle  = 'solid';
      npDropzone.style.borderColor  = '#198754';
      npRevert.style.display = 'flex';
    };
    reader.readAsDataURL(file);
  }

  npRevert.addEventListener('click', e => {
    e.stopPropagation();
    npImageInput.value      = '';
    npPreview.style.display = 'none';
    npPreview.src           = '';
    npPlaceholder.style.display = 'block';
    npRevert.style.display  = 'none';
    npDropzone.style.borderStyle = 'dashed';
    npDropzone.style.borderColor = '#ccc';
    npDropzone.style.background  = '#fafafa';
  });

  npDropzone.addEventListener('click', () => npImageInput.click());
  npImageInput.addEventListener('change', function() {
    if (this.files[0]) showNpPreview(this.files[0]);
  });
  npDropzone.addEventListener('dragover', e => {
    e.preventDefault();
    npDropzone.style.borderColor = '#198754';
    npDropzone.style.background  = '#f0fff4';
  });
  npDropzone.addEventListener('dragleave', e => {
    if (!npDropzone.contains(e.relatedTarget)) {
      npDropzone.style.borderColor = '#ccc';
      npDropzone.style.background  = '#fafafa';
    }
  });
  npDropzone.addEventListener('drop', e => {
    e.preventDefault();
    npDropzone.style.background = '#fafafa';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const dt = new DataTransfer();
      dt.items.add(file);
      npImageInput.files = dt.files;
      showNpPreview(file);
    }
  });

  const abImage         = document.getElementById('ab-image');
  const fbBox           = document.getElementById('img-feedback');
  const fbList          = document.getElementById('img-feedback-list');
  const fbTitle         = document.getElementById('img-feedback-title');
  const fbSpinner       = document.getElementById('img-spinner');
  const fbStats         = document.getElementById('img-stats');
  const brightnessVal   = document.getElementById('img-brightness-val');
  const rembgSection    = document.getElementById('img-rembg-section');
  const rembgPreview    = document.getElementById('img-rembg-preview');
  const coveragePct     = document.getElementById('img-coverage-pct');
  const cutoffPct       = document.getElementById('img-cutoff-pct');
  const gradeRow        = document.getElementById('img-grade-row');
  const gradeVal        = document.getElementById('img-grade-val');
  const ripenessVal     = document.getElementById('img-ripeness-val');
  const colourVal       = document.getElementById('img-colour-val');
  const sizeVal         = document.getElementById('img-size-val');

  const GRADE_COLOURS = { A: '#1a7a3c', B: '#3a7abf', C: '#c97a00', D: '#c94000', Rejected: '#991111' };
  let _lastGradeResult = null;

  function _setSubmitDisabled(disabled) {
    const btn = _batchForm?.querySelector('button[type="submit"]');
    if (btn) btn.disabled = disabled;
  }

  function setProductLock(lock) {
    if (!_batchForm) return;
    const uploadLabel = document.getElementById('ab-upload-label');
    const abImg = document.getElementById('ab-image');
    if (lock) {
      // No product selected: lock everything including the image picker
      _batchForm.classList.add('form--locked');
      _batchForm.querySelectorAll(
        'input:not([type="hidden"]):not(#batch-product), select:not(#batch-product), textarea'
      ).forEach(el => { el.disabled = true; });
      _setSubmitDisabled(true);
      if (uploadLabel) { uploadLabel.style.opacity = '0.45'; uploadLabel.style.pointerEvents = 'none'; }
      fbBox.style.display   = 'none';
      fbStats.style.display = 'none';
    } else {
      // Product selected: keep fields greyed until image is analysed, but open image picker
      _batchForm.dataset.rejected = '';
      _batchForm.classList.add('form--locked');
      _batchForm.querySelectorAll(
        'input:not([type="hidden"]):not(#batch-product):not(#ab-image), select:not(#batch-product), textarea'
      ).forEach(el => { el.disabled = true; });
      if (abImg) abImg.disabled = false;
      _setSubmitDisabled(true);
      if (uploadLabel) { uploadLabel.style.opacity = ''; uploadLabel.style.pointerEvents = ''; }
    }
  }

  const _batchForm = document.querySelector('#pane-batch form');
  if (_batchForm) {
    _batchForm.addEventListener('submit', e => {
      if (_batchForm.dataset.rejected === '1') {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    });
  }

  function lockBatchForm(lock) {
    if (!_batchForm) return;
    _batchForm.dataset.rejected = lock ? '1' : '';
    _batchForm.classList.toggle('form--locked', lock);
    _batchForm.querySelectorAll(
      'input:not([type="hidden"]):not(#ab-image), select:not(#batch-product), textarea, button[type="submit"]'
    ).forEach(el => { el.disabled = lock; });
  }

  function toggleMetric(btn) {
    const body = btn.nextElementSibling;
    const chevron = btn.querySelector('.gm-metric-chevron');
    const isHidden = getComputedStyle(body).display === 'none';
    body.style.display = isHidden ? 'block' : 'none';
    chevron.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
  }

  function switchGmView(view) {
    document.getElementById('gm-basic-panel').style.display    = view === 'basic'    ? '' : 'none';
    document.getElementById('gm-advanced-panel').style.display = view === 'advanced' ? '' : 'none';
    document.getElementById('gm-btn-basic').classList.toggle('active',    view === 'basic');
    document.getElementById('gm-btn-advanced').classList.toggle('active', view === 'advanced');
  }

  function buildFormulaHtml(r) {
    const m   = r.metrics          || {};
    const ex  = r.explanation      || {};
    const cb  = r.colour_breakdown || {};
    const ripeness  = m.ripeness ?? 0;
    const colour    = m.colour   ?? 0;
    const size      = m.size     ?? 0;
    const composite = ex.composite_score ?? ((ripeness + colour + size) / 3);
    const rawConf   = ex.health_confidence ?? ripeness;
    const isRotten  = r.prediction === 'Rotten';
    const method    = ex.method || 'unknown';
    const isDual    = cb.method === 'dual_bhattacharyya';
    const typeKnown = cb.known ?? ex.known_type ?? false;
    const typeName  = cb.type_name || r.fruit_type || 'unknown';
    const typeConf  = cb.type_confidence ?? ex.type_confidence;
    const pd        = r.proportion_details || null;
    const ML_LABELS = {
      mtl:  'Multi-task learning (MTL)',
      stl:  'Single-task neural network (STL)',
      'heuristic-pixel-rubric': 'Pixel heuristic (no ML model loaded)',
    };
    const modelLabel = r.model_display_name
      ? `<strong>${r.model_display_name}</strong>`
      : `<span style="color:#888;">${ML_LABELS[method] || method}</span>`;
    const THRESHOLDS = [
      { grade: 'A', avg: 85 }, { grade: 'B', avg: 75 },
      { grade: 'C', avg: 65 }, { grade: 'D', avg: 0  },
    ];
    const matched    = THRESHOLDS.find(t => t.grade === r.overall_grade);
    const gradeColor = GRADE_COLOURS[r.overall_grade] || '#333';

    const typePill = typeKnown
      ? `<span style="background:#f0f4ff;color:#2a5abf;padding:1px 8px;border-radius:12px;font-weight:600;border:1px solid #b0c4f0;">${typeName}</span>`
      : `<span style="background:#f5f5f5;color:#888;padding:1px 8px;border-radius:12px;font-weight:600;border:1px solid #ddd;font-style:italic;">Unknown</span>`;
    const typeConf$ = typeConf != null ? ` <span style="color:#888;font-size:0.85em;">(${typeConf.toFixed(1)}%${typeKnown ? '' : ' – below threshold'})</span>` : '';
    const typeBadge = `${typePill}${typeConf$}`;
    const healthBg     = isRotten ? '#fff5f4' : '#f0fff4';
    const healthColor  = isRotten ? '#991111' : '#1a7a3c';
    const healthBorder = isRotten ? '#f0ccc8' : '#b2dfcd';
    const healthBadge  = `<span style="background:${healthBg};color:${healthColor};padding:1px 8px;border-radius:12px;font-weight:600;border:1px solid ${healthBorder};">${r.prediction}</span> <span style="color:#888;font-size:0.85em;">(${rawConf.toFixed(1)}%)</span>`;

    // Colour step rows differ by method
    let colourRows, colourNote;
    if (isDual) {
      const dH = cb.d_healthy, dR = cb.d_rotten, wH = cb.w_healthy, wR = cb.w_rotten, g = cb.gamma;
      const fmt = v => (v != null ? v : '?');
      const dualMatchesFinal = cb.dual_score === cb.final_score;
      colourRows = [
        ['Method',       '<code>Bhattacharyya dual histogram similarity</code>'],
        ['Formula',      `<code>score = w<sub>H</sub> / (w<sub>H</sub> + w<sub>R</sub>) &times; 100</code> &nbsp; where &nbsp; <code>w = e<sup>-&#947;d</sup></code>, <code>&#947;&nbsp;=&nbsp;${fmt(g)}</code>`],
        ['d<sub>H</sub> <span style="color:#888;font-weight:400;">(dist. to healthy)</span>', `<code>${fmt(dH)} &rarr; w<sub>H</sub> = exp(&minus;${fmt(g)}&times;${fmt(dH)}) = <strong>${fmt(wH)}</strong></code>`],
        ['d<sub>R</sub> <span style="color:#888;font-weight:400;">(dist. to rotten)</span>',  `<code>${fmt(dR)} &rarr; w<sub>R</sub> = exp(&minus;${fmt(g)}&times;${fmt(dR)}) = <strong>${fmt(wR)}</strong></code>`],
        ['Dual score',   `<code>${fmt(wH)} / (${fmt(wH)} + ${fmt(wR)}) &times; 100</code> = <strong>${cb.dual_score}%</strong>`, dualMatchesFinal ? 'total' : ''],
        ...(!dualMatchesFinal ? [['Colour score',
          `<code>max(dual&nbsp;${cb.dual_score}%,&nbsp;generic&nbsp;${cb.generic_score}%)</code> = <strong>${cb.final_score}%</strong>`,
          'total']] : []),
      ];
      colourNote = dualMatchesFinal
        ? `Bhattacharyya: compares the full HSV histogram shape against a ${typeName}-specific reference built from training images. A lower distance means a closer colour match to healthy ${typeName}.`
        : `Generic vibrancy used as floor: measures mean HSV saturation percentile against all healthy training images — a score of ${cb.generic_score}% means this image is more vibrant than ${cb.generic_score}% of healthy training examples. It exceeded the Bhattacharyya dual score (${cb.dual_score}%), which may have been reduced by lighting or angle differences vs the reference.`;
    } else {
      const fallbackReason = typeKnown
        ? `Produce type identified as <em>${typeName}</em>, but no colour reference exists for it in the training set. Falling back to generic vibrancy percentile.`
        : `Produce type could not be identified with sufficient confidence${typeConf != null ? ` (${typeConf.toFixed(1)}% - below 50% threshold)` : ''}. Dual Bhattacharyya grading requires a known type. Falling back to generic vibrancy percentile.`;
      colourRows = [
        ['Method',       '<code>Vibrancy percentile (fallback)</code>'],
        ['Colour score', `<strong>${colour.toFixed(1)}%</strong>`, 'total'],
      ];
      colourNote = `${fallbackReason} Generic vibrancy measures mean HSV saturation percentile against all healthy training images — a score of ${colour.toFixed(1)}% means this image is more vibrant than ${colour.toFixed(1)}% of healthy training examples.`;
    }

    const steps = [
      {
        title: '1 - Health & Type Classification + Ripeness Score',
        rows: [
          ['Model',        modelLabel],
          ['Health prediction', healthBadge],
          ['Type prediction', typeBadge],
          ['Ripeness score', `<code>health confidence</code> = <strong>${rawConf.toFixed(1)}%</strong>`, 'total'],
        ],
        warn: isRotten,
        note: isRotten ? 'Classified as Rotten - item is Rejected regardless of colour or proportion scores.' : null,
      },

      {
        title: `2 - Colour Score (${isDual ? 'Bhattacharyya Dual' : 'Vibrancy Percentile'})`,
        rows: colourRows,
        img: cb.histogram_b64 || null,
        noteInfo: colourNote,
      },
      {
        title: '3 - Proportion Score',
        rows: [
          ['Method',           '<code>Contour solidity = item area / convex hull area</code>'],
          ['Proportion score', pd && pd.hull_area
            ? `<code>${pd.contour_area.toLocaleString()} / ${pd.hull_area.toLocaleString()} &times; 100</code> = <strong>${size.toFixed(1)}%</strong>`
            : `<strong>${size.toFixed(1)}%</strong>`, 'total'],
        ],
      },
    ];

    if (!isRotten) {
      // Thermometer bar: zones coloured by grade band, marker at composite score
      const ZONES = [
        { grade: 'D', lo: 0,  hi: 65, color: '#aaa' },
        { grade: 'C', lo: 65, hi: 75, color: '#e8a020' },
        { grade: 'B', lo: 75, hi: 85, color: '#3a7abf' },
        { grade: 'A', lo: 85, hi: 100, color: '#1a7a3c' },
      ];
      const thermometer = (() => {
        const score = Math.min(composite, 100);
        // Top tick marks at each boundary
        const ticks = [65, 75, 85].map(t =>
          `<div style="position:absolute;left:${t}%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.18);"></div>
           <div style="position:absolute;left:${t}%;top:-14px;font-size:0.62rem;color:#999;transform:translateX(-50%);">${t}</div>`
        ).join('');
        // Colour fill zones
        const fills = ZONES.map(z => {
          const w = z.hi - z.lo;
          return `<div style="position:absolute;left:${z.lo}%;width:${w}%;height:100%;background:${z.color};opacity:0.55;border-radius:${z.lo===0?'7px 0 0 7px':''}${z.hi===100?'0 7px 7px 0':''}"></div>`;
        }).join('');
        // Grade labels below bar
        const labels = ZONES.map(z => {
          const mid = z.lo + (z.hi - z.lo) / 2;
          return `<div style="position:absolute;left:${mid}%;top:18px;font-size:0.72rem;color:${z.color};font-weight:800;transform:translateX(-50%);">${z.grade}</div>`;
        }).join('');
        // Score marker
        const marker = `<div style="position:absolute;left:${score}%;top:-4px;bottom:-4px;width:4px;background:${gradeColor};border-radius:3px;transform:translateX(-50%);box-shadow:0 0 4px 1px ${gradeColor};z-index:2;"></div>`;
        return `<div style="position:relative;padding:18px 8px 32px;background:transparent;">
          <div style="position:relative;height:14px;background:#e8e8e8;border-radius:7px;overflow:visible;">${fills}${ticks}${marker}</div>
          <div style="position:relative;height:20px;">${labels}</div>
        </div>`;
      })();
      steps.push({
        title: '5 - Composite Grade',
        highlight: true,
        rows: [
          ['Formula',     '<code>(ripeness + colour + proportion) / 3</code>'],
          ['Calculation', `<code>(${ripeness.toFixed(1)} + ${colour.toFixed(1)} + ${size.toFixed(1)}) / 3</code> = <strong>${composite.toFixed(1)}</strong>`],
          ['Thresholds',  `<span style="font-size:0.8rem;"><strong style="color:#1a7a3c;">A</strong> &ge; 85 &nbsp; <strong style="color:#3a7abf;">B</strong> &ge; 75 &nbsp; <strong style="color:#e8a020;">C</strong> &ge; 65 &nbsp; <strong style="color:#888;">D</strong> &lt; 65</span>`],
          ['Result',      `<strong style="color:${gradeColor};font-size:1rem;">${r.overall_grade}</strong>`, 'total'],
        ],
        thermometer,
      });
    }

    return steps.map(s => `
      <div class="gm-formula-step${s.highlight ? ' gm-formula-step--result' : s.warn ? ' gm-formula-step--warn' : ''}">
        <div class="gm-formula-step-title">${s.title}</div>
        ${s.imgLeft ? `
          <div style="display:flex;gap:10px;align-items:flex-start;padding:8px 12px 0;">
            <img src="data:image/jpeg;base64,${s.imgLeft}" style="flex:0 0 auto;width:140px;border-radius:4px;border:1px solid #e0e0e0;object-fit:contain;">
            <table class="gm-formula-table" style="flex:1;margin:0;">
              ${s.rows.map(([k, v, cls='']) => `<tr class="${cls==='total'?'gm-formula-row--total':''}"><td class="gm-fk">${k}</td><td class="gm-fv">${v}</td></tr>`).join('')}
            </table>
          </div>` : `
        <table class="gm-formula-table">
          ${s.rows.map(([k, v, cls='']) => `<tr class="${cls==='total'?'gm-formula-row--total':''}"><td class="gm-fk">${k}</td><td class="gm-fv">${v}</td></tr>`).join('')}
        </table>`}
        ${s.thermometer ? s.thermometer : ''}
        ${s.note     ? `<p class="gm-formula-note">${s.note}</p>` : ''}
        ${s.noteInfo ? `<p style="margin:0;padding:6px 12px 8px;font-size:0.76rem;color:#555;background:#f5f8ff;border-top:1px solid #d0d8f0;">${s.noteInfo}</p>` : ''}
        ${s.img  ? `<div style="background:#f5f5f5;padding:6px 10px 10px;"><img src="data:image/png;base64,${s.img}" style="display:block;width:100%;border-radius:4px;border:1px solid #ddd;"></div>` : ''}
      </div>`).join('');
  }

  function openGradeModal() {
    const r = _lastGradeResult;
    if (!r) return;
    const grade = r.overall_grade;
    const m = r.metrics || {};
    const exp = r.explanation || {};
    // Badge
    const badge = document.getElementById('gm-grade-badge');
    badge.textContent = grade;
    badge.style.color = GRADE_COLOURS[grade] || '#333';
    // Colour border on result summary
    const summary = document.getElementById('gm-result-summary');
    summary.style.borderLeftColor = GRADE_COLOURS[grade] || '#ccc';
    summary.style.background = grade === 'Rejected' ? '#fff5f4' : '#f7f7f7';
    // Rejected notice
    document.getElementById('gm-rejected-notice').style.display = grade === 'Rejected' ? '' : 'none';
    // Metric bars - dim colour/proportion when Rejected (health check overrides everything)
    const barsEl = document.getElementById('gm-metrics-bars');
    barsEl.innerHTML = '';
    const cb2 = r.colour_breakdown || {};
    const isDual2 = cb2.method === 'dual_bhattacharyya';
    const genericFloor2 = isDual2 && cb2.dual_score !== cb2.final_score;
    const colourNote2 = isDual2 && !genericFloor2
      ? `Bhattacharyya histogram match vs ${cb2.type_name || 'type-specific'} reference`
      : genericFloor2
        ? `Generic vibrancy percentile used (dual ${cb2.dual_score}% &lt; generic ${cb2.generic_score}%)`
        : `HSV saturation percentile vs healthy training images`;
    const metrics = [
      { label: 'Ripeness',   value: m.ripeness, decisive: true,              note: 'Softmax confidence on health prediction' },
      { label: 'Colour',     value: m.colour,   decisive: grade !== 'Rejected', note: colourNote2 },
      { label: 'Proportion', value: m.size,     decisive: grade !== 'Rejected', note: 'Contour solidity (item area / convex hull area)' },
    ];
    metrics.forEach(({ label, value, decisive, note }) => {
      const pct = value != null ? value.toFixed(1) : '-';
      const barW = value != null ? Math.min(value, 100) : 0;
      const barColor = decisive ? (GRADE_COLOURS[grade] || '#888') : '#ccc';
      barsEl.insertAdjacentHTML('beforeend', `
        <div style="${decisive ? '' : 'opacity:0.45;'}">
          <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:2px;">
            <span style="color:#555;">${label}${decisive ? '' : ' <em style="font-weight:400;font-size:0.75rem;">(not decisive)</em>'}</span>
            <span style="font-weight:600;">${pct}%</span>
          </div>
          <div style="height:7px;background:#e0e0e0;border-radius:4px;overflow:hidden;">
            <div style="height:100%;width:${barW}%;background:${barColor};border-radius:4px;transition:width 0.4s;"></div>
          </div>
          <div style="font-size:0.68rem;color:#999;margin-top:2px;">${note}</div>
        </div>`);
    });
    // Composite score thermometer (modal summary)
    const cs = exp.composite_score ?? ((m.ripeness + m.colour + m.size) / 3);
    const compositeWrap = document.getElementById('gm-composite-bar-wrap');
    const compositeEl   = document.getElementById('gm-composite-bar');
    if (grade !== 'Rejected' && cs != null) {
      const gc = GRADE_COLOURS[grade] || '#888';
      const score = Math.min(cs, 100);
      const CZONES = [
        { grade: 'D', lo: 0,  hi: 65, color: '#aaa' },
        { grade: 'C', lo: 65, hi: 75, color: '#e8a020' },
        { grade: 'B', lo: 75, hi: 85, color: '#3a7abf' },
        { grade: 'A', lo: 85, hi: 100, color: '#1a7a3c' },
      ];
      const fills  = CZONES.map(z => `<div style="position:absolute;left:${z.lo}%;width:${z.hi-z.lo}%;height:100%;background:${z.color};opacity:0.55;border-radius:${z.lo===0?'5px 0 0 5px':''}${z.hi===100?'0 5px 5px 0':''}"></div>`).join('');
      const ticks  = [65,75,85].map(t => `<div style="position:absolute;left:${t}%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.18);"></div>`).join('');
      const marker = `<div style="position:absolute;left:${score}%;top:-3px;bottom:-3px;width:4px;background:${gc};border-radius:3px;transform:translateX(-50%);box-shadow:0 0 5px 1px ${gc};z-index:2;"></div>`;
      const labels = CZONES.map(z => {
        const mid = z.lo + (z.hi - z.lo) / 2;
        return `<div style="position:absolute;left:${mid}%;transform:translateX(-50%);font-size:0.7rem;color:${z.color};font-weight:800;">${z.grade}</div>`;
      }).join('');
      compositeEl.innerHTML = `
        <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:6px;">
          <span style="color:#555;font-weight:700;text-transform:uppercase;font-size:0.72rem;letter-spacing:0.05em;">Quality score</span>
          <span style="font-weight:800;color:${gc};">${cs.toFixed(1)}%</span>
        </div>
        <div style="position:relative;height:10px;background:#e0e0e0;border-radius:5px;overflow:visible;">${fills}${ticks}${marker}</div>
        <div style="position:relative;height:16px;margin-top:3px;">${labels}</div>`;
      compositeWrap.style.display = '';
    } else {
      compositeWrap.style.display = 'none';
    }
    // Method note
    const method = exp.method || 'unknown';
    const methodLabels = { mtl: 'Multi-task neural network (MTL)', stl: 'Single-task neural network (STL)', 'heuristic-pixel-rubric': 'Heuristic pixel fallback (no model loaded)' };
    document.getElementById('gm-method-note').textContent =
      `Inference method: ${methodLabels[method] || method}. Health confidence: ${exp.health_confidence != null ? exp.health_confidence.toFixed(1) + '%' : '-'}.`;
    // XAI images (advanced panel)
    const xai = r.xai || {};
    const maskImg = document.getElementById('gm-xai-mask');
    const maskNa  = document.getElementById('gm-xai-mask-na');
    const camImg  = document.getElementById('gm-xai-cam');
    const camNa   = document.getElementById('gm-xai-cam-na');
    if (xai.mask_b64) {
      maskImg.src = `data:image/png;base64,${xai.mask_b64}`;
      maskImg.style.display = '';
      maskNa.style.display  = 'none';
    } else {
      maskImg.style.display = 'none';
      maskNa.style.display  = '';
    }
    if (xai.grad_cam_b64) {
      camImg.src = `data:image/png;base64,${xai.grad_cam_b64}`;
      camImg.style.display = '';
      camNa.style.display  = 'none';
    } else {
      camImg.style.display = 'none';
      camNa.style.display  = '';
    }
    const propImg = document.getElementById('gm-xai-proportion');
    const propNa  = document.getElementById('gm-xai-proportion-na');
    if (xai.proportion_overlay_b64) {
      propImg.src = `data:image/jpeg;base64,${xai.proportion_overlay_b64}`;
      propImg.style.display = '';
      propNa.style.display  = 'none';
    } else {
      propImg.style.display = 'none';
      propNa.style.display  = '';
    }
    // Formula breakdown
    document.getElementById('gm-formula-content').innerHTML = buildFormulaHtml(r);
    // Reset to summary view and show modal
    switchGmView('basic');
    document.getElementById('grade-modal-backdrop').style.display = '';
    document.getElementById('grade-modal').style.display = '';
    document.body.style.overflow = 'hidden';
  }

  function closeGradeModal() {
    document.getElementById('grade-modal-backdrop').style.display = 'none';
    document.getElementById('grade-modal').style.display = 'none';
    document.body.style.overflow = '';
  }

  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeGradeModal(); closeDisputeModal(); } });

  function openDisputeModal() {
    const descField = document.getElementById('grade-complaint-desc');
    if (!descField.value && _lastGradeResult) {
      const r = _lastGradeResult;
      const m = r.metrics || {};
      descField.value = `I disagree with the AI grade of "${r.overall_grade}" for this item.\n\nMetrics: Ripeness ${m.ripeness ?? '-'}%, Colour ${m.colour ?? '-'}%, Proportion ${m.size ?? '-'}%.`;
    }
    document.getElementById('dispute-modal-backdrop').style.display = '';
    document.getElementById('dispute-modal').style.display = '';
    document.body.style.overflow = 'hidden';
  }

  function closeDisputeModal() {
    document.getElementById('dispute-modal-backdrop').style.display = 'none';
    document.getElementById('dispute-modal').style.display = 'none';
    document.body.style.overflow = '';
  }

  async function submitGradeComplaint() {
    const r = _lastGradeResult;
    const m = r ? (r.metrics || {}) : {};
    const grade = r ? r.overall_grade : 'unknown';
    const descField = document.getElementById('grade-complaint-desc');
    const contextNote = `\n\n[AI grade: ${grade} | Ripeness: ${m.ripeness ?? '-'}% | Colour: ${m.colour ?? '-'}% | Proportion: ${m.size ?? '-'}%]`;
    const fullDesc = descField.value + (descField.value.includes('[AI grade:') ? '' : contextNote);
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    fd.append('name',        document.getElementById('gc-name').value);
    fd.append('email',       document.getElementById('gc-email').value);
    fd.append('category',    'Quality Issue');
    fd.append('description', fullDesc);
    try {
      await fetch('/complaint/', { method: 'POST', body: fd, redirect: 'follow' });
    } catch (ex) { /* ignore network error */ }
    document.getElementById('grade-complaint-form').style.display = 'none';
    document.getElementById('grade-complaint-sent').style.display = '';
  }

  async function analyseImage(file) {
    // Draw image to canvas - used for brightness check AND to produce a
    // JPEG blob for the server (handles HEIC and other exotic formats PIL can't open)
    const { brightnessTips, avgLum, jpegBlob } = await new Promise(resolve => {
      const img = new Image();
      img.onload = function() {
        const W = img.naturalWidth, H = img.naturalHeight;
        const canvas = document.createElement('canvas');
        canvas.width = W; canvas.height = H;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        const data = ctx.getImageData(0, 0, W, H).data;
        let lumSum = 0;
        const total = W * H;
        for (let i = 0; i < data.length; i += 4)
          lumSum += 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
        const lum = lumSum / total;
        const tips = [];
        if (lum < 80)
          tips.push(`Image is too dark (brightness ${(lum/255*100).toFixed(0)}%). Move to better lighting or increase brightness.`);
        else if (lum > 230)
          tips.push(`Image is overexposed (brightness ${(lum/255*100).toFixed(0)}%). Reduce direct light or avoid flash.`);
        URL.revokeObjectURL(img.src);
        canvas.toBlob(blob => resolve({ brightnessTips: tips, avgLum: lum, jpegBlob: blob }), 'image/jpeg', 0.85);
      };
      img.src = URL.createObjectURL(file);
    });

    // Reset state from any prior analysis — keep submit disabled until analysis completes
    _lastGradeResult = null;
    lockBatchForm(false);
    _setSubmitDisabled(true);
    document.getElementById('grade-complaint-form').style.display = '';
    document.getElementById('grade-complaint-sent').style.display = 'none';
    document.getElementById('grade-complaint-desc').value = '';

    // Show loading state while rembg runs server-side
    fbBox.style.background = '#f5f5f5';
    fbBox.style.borderColor = '#ccc';
    fbTitle.textContent = 'Analysing image…';
    fbList.innerHTML = '';
    fbStats.style.display = 'none';
    rembgSection.style.display = 'none';
    fbSpinner.style.display = 'inline-block';
    fbBox.style.display = '';

    // --- step 1: coverage/quality check via rembg (canvas JPEG for format compat) ---
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let coverageTips = [];
    let serverResult = null;
    try {
      const fd = new FormData();
      fd.append('image', jpegBlob, 'image.jpg');
      fd.append('csrfmiddlewaretoken', csrf);
      const resp = await fetch('/inventory_upload/analyse/', { method: 'POST', body: fd });
      if (resp.ok) {
        serverResult = await resp.json();
        if (serverResult.tips) coverageTips = serverResult.tips;
      }
    } catch (e) { /* non-critical */ }

    // --- step 2: AI grading - original file, only if no quality issues and produce category ---
    const selectedCategory = productSelect.selectedOptions[0]?.dataset.category || '';
    const isProduce = ['Vegetable', 'Fruit'].includes(selectedCategory);
    let gradeResult = null;
    const allTipsSoFar = [...brightnessTips, ...coverageTips];
    if (allTipsSoFar.length === 0 && isProduce) {
      try {
        const fd = new FormData();
        fd.append('image', file, file.name);
        fd.append('category', selectedCategory);
        fd.append('csrfmiddlewaretoken', csrf);
        const resp = await fetch('/inventory_upload/grade/', { method: 'POST', body: fd });
        if (resp.ok) gradeResult = await resp.json();
      } catch (e) { /* non-critical */ }
    }

    const tips = [...brightnessTips, ...coverageTips];
    if (tips.length) {
      fbBox.style.background = '#fff8e1';
      fbBox.style.borderColor = '#f6c90e';
      fbTitle.textContent = 'Image quality suggestions:';
      fbList.innerHTML = tips.map(t => `<li>${t}</li>`).join('');
      lockBatchForm(true);
    } else {
      fbBox.style.background = '#f0fff4';
      fbBox.style.borderColor = '#198754';
      fbTitle.textContent = 'Image looks good!';
      fbList.innerHTML = '';
      lockBatchForm(false);
    }
    if (!isProduce && selectedCategory) {
      fbList.insertAdjacentHTML('beforeend',
        `<li style="list-style:none;margin-top:6px;padding:5px 8px;background:#f0f4ff;border-radius:4px;color:#555;font-size:0.82em;border-left:3px solid #7090d0;">` +
        `AI quality grading is only available for Fruit and Vegetable products.</li>`);
    }

    fbSpinner.style.display = 'none';
    brightnessVal.textContent = `${(avgLum / 255 * 100).toFixed(0)}%`;
    fbStats.style.display = 'flex';

    if (serverResult && serverResult.preview) {
      coveragePct.textContent = `${(serverResult.coverage * 100).toFixed(1)}%`;
      cutoffPct.textContent = serverResult.cutoff != null ? `${serverResult.cutoff.toFixed(0)}%` : '-';
      rembgPreview.src = `data:image/jpeg;base64,${serverResult.preview}`;
      rembgSection.style.display = '';
    } else {
      coveragePct.textContent = '-';
      cutoffPct.textContent = '-';
      rembgSection.style.display = 'none';
    }

    if (gradeResult && gradeResult.overall_grade) {
      _lastGradeResult = gradeResult;
      const grade = gradeResult.overall_grade;
      const m = gradeResult.metrics || {};
      const ex = gradeResult.explanation || {};
      const gradeColor = GRADE_COLOURS[grade] || '#888';
      const isRejected = grade === 'Rejected';

      // Grade badge
      gradeVal.textContent = grade;
      gradeVal.style.color = gradeColor;

      // Quality score thermometer
      const cs = ex.composite_score ?? ((m.ripeness + m.colour + m.size) / 3);
      const compositeBar    = document.getElementById('img-composite-bar');
      const compositeLabels = document.getElementById('img-composite-labels');
      const compositeVal    = document.getElementById('img-composite-val');
      const compositeRow    = document.getElementById('img-composite-row');
      if (!isRejected && cs != null) {
        const score = Math.min(cs, 100);
        const CZONES = [
          { grade: 'D', lo: 0,  hi: 65, color: '#aaa' },
          { grade: 'C', lo: 65, hi: 75, color: '#e8a020' },
          { grade: 'B', lo: 75, hi: 85, color: '#3a7abf' },
          { grade: 'A', lo: 85, hi: 100, color: '#1a7a3c' },
        ];
        compositeBar.innerHTML =
          CZONES.map(z => {
            const w = z.hi - z.lo;
            return `<div style="position:absolute;left:${z.lo}%;width:${w}%;height:100%;background:${z.color};opacity:0.55;border-radius:${z.lo===0?'6px 0 0 6px':''}${z.hi===100?'0 6px 6px 0':''}"></div>`;
          }).join('') +
          [65, 75, 85].map(t =>
            `<div style="position:absolute;left:${t}%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.2);"></div>`
          ).join('') +
          `<div style="position:absolute;left:${score}%;top:-4px;bottom:-4px;width:4px;background:${gradeColor};border-radius:3px;transform:translateX(-50%);box-shadow:0 0 4px 1px ${gradeColor};z-index:2;"></div>`;
        compositeLabels.innerHTML =
          CZONES.map(z => {
            const mid = z.lo + (z.hi - z.lo) / 2;
            return `<div style="position:absolute;left:${mid}%;transform:translateX(-50%);font-size:0.7rem;color:${z.color};font-weight:800;">${z.grade}</div>`;
          }).join('');
        compositeVal.textContent = `${cs.toFixed(1)}%`;
        compositeVal.style.color = gradeColor;
        // Tint row background with grade colour
        const hex = gradeColor.replace('#','');
        const r16 = parseInt(hex.slice(0,2),16), g16 = parseInt(hex.slice(2,4),16), b16 = parseInt(hex.slice(4,6),16);
        compositeRow.style.background = `rgba(${r16},${g16},${b16},0.07)`;
        compositeRow.style.display = '';
      } else {
        compositeRow.style.display = 'none';
      }

      // Individual metric bars
      const metricDefs = [
        { valEl: ripenessVal, barId: 'img-ripeness-bar', rowId: 'img-ripeness-row', value: m.ripeness },
        { valEl: colourVal,   barId: 'img-colour-bar',   rowId: 'img-colour-row',   value: m.colour  },
        { valEl: sizeVal,     barId: 'img-size-bar',     rowId: 'img-size-row',     value: m.size    },
      ];
      metricDefs.forEach(({ valEl, barId, rowId, value }) => {
        valEl.textContent = value != null ? `${value.toFixed(1)}%` : '-';
        const bar = document.getElementById(barId);
        const row = document.getElementById(rowId);
        bar.style.width = value != null ? `${Math.min(value, 100)}%` : '0%';
        bar.style.background = isRejected ? '#ccc' : gradeColor;
        bar.style.opacity = isRejected ? '0.4' : '0.8';
        row.style.opacity = isRejected ? '0.45' : '1';
      });

      gradeRow.style.display = '';
      // Pre-fill quality class radio - map Rejected → Discounted
      const radioVal = grade === 'Rejected' ? 'Discounted' : grade;
      const radio = document.querySelector(`input[name="quality_class"][value="${radioVal}"]`);
      if (radio) radio.click();
      // Rejected: lock the rest of the form and override box colour
      if (grade === 'Rejected') {
        fbBox.style.background = '#fff0f0';
        fbBox.style.borderColor = '#cc2200';
        fbTitle.textContent = 'Item rejected. Please try with a different item.';
        lockBatchForm(true);
      } else {
        lockBatchForm(false);
      }
      // Effective price in grade panel - hidden for Rejected
      const epRow   = document.getElementById('img-effective-price-row');
      const epEl    = document.getElementById('img-effective-price');
      const epLabel = document.getElementById('img-effective-label');
      const base = getSelectedBasePrice();
      if (!isNaN(base) && grade !== 'Rejected') {
        const disc = discounts[radioVal] ?? 0;
        const ep = (base * (1 - disc)).toFixed(2);
        epEl.textContent    = `£${ep}`;
        epLabel.textContent = labels[radioVal] ? `(${labels[radioVal]})` : '';
        epRow.style.display = '';
      } else {
        epRow.style.display = 'none';
      }
      // Hide base price and effective price rows below the form when Rejected
      basePriceDisp.style.display = grade === 'Rejected' ? 'none' : (isNaN(base) ? 'none' : '');
      if (grade === 'Rejected') {
        effectivePriceDisplay.textContent = '-';
        priceSuggLabel.textContent = '';
      }
    } else {
      gradeRow.style.display = 'none';
    }

    fbBox.style.display = '';
  }

  if (abImage) {
    abImage.addEventListener('change', function() {
      const span = this.closest('label.upload').querySelector('.upload-label');
      span.textContent = this.files[0] ? this.files[0].name : 'Select image (auto-compressed on upload)';
      if (this.files[0]) analyseImage(this.files[0]);
      else { fbBox.style.display = 'none'; }
    });
  }

  function lockSeasonEnd(startId, endId) {
    const s = document.getElementById(startId);
    const e = document.getElementById(endId);
    if (!s || !e) return;
    function update() {
      Array.from(e.options).forEach((opt, i) => { opt.disabled = i < s.selectedIndex; });
      if (e.selectedIndex < s.selectedIndex) e.selectedIndex = s.selectedIndex;
    }
    s.addEventListener('change', update);
    update();
  }

  const discounts = { A: 0, B: 0.15, C: 0.30, D: 0.45, Discounted: 0.50 };
  const labels    = { A: 'base price', B: '−15% from base', C: '−30% from base', D: '−45% from base', Discounted: '−50% from base (suggested)' };

  const productSelect  = document.getElementById('batch-product');
  const priceInput     = document.getElementById('batch-price');
  const priceSuggLabel = document.getElementById('price-suggestion');
  const basePriceDisp  = document.getElementById('base-price-display');
  const basePriceVal   = document.getElementById('base-price-value');
  const effectivePriceDisplay = document.getElementById('effective-price-display');

  function getSelectedBasePrice() {
    const opt = productSelect.options[productSelect.selectedIndex];
    return opt ? parseFloat(opt.dataset.basePrice) : NaN;
  }

  function updateSuggestedPrice() {
    const base = getSelectedBasePrice();
    const qc   = document.querySelector('input[name="quality_class"]:checked')?.value;
    if (isNaN(base) || !qc) {
      priceSuggLabel.textContent      = '';
      effectivePriceDisplay.textContent = '-';
      return;
    }
    const discount  = discounts[qc] ?? 0;
    const effective = (base * (1 - discount)).toFixed(2);
    priceInput.value = effective;
    effectivePriceDisplay.textContent = `£${effective}`;
    priceSuggLabel.textContent        = `(${labels[qc]})`;
  }

  const PRODUCT_SEASONS = JSON.parse(document.getElementById('product-season-data').textContent);
  const MONTH_NUMS = {
    'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
    'July':7,'August':8,'September':9,'October':10,'November':11,'December':12
  };

  function updateHarvestDateBounds() {
    const harvestPicker = document.getElementById('harvest_date');
    if (!harvestPicker) return;
    const today = new Date();
    const pad = n => String(n).padStart(2, '0');
    const todayStr = `${today.getFullYear()}-${pad(today.getMonth()+1)}-${pad(today.getDate())}`;
    harvestPicker.max = todayStr;
    const season = PRODUCT_SEASONS[productSelect.value];
    if (!season || season.allYear) { harvestPicker.min = ''; return; }
    const startNum = MONTH_NUMS[season.seasonStart];
    if (!startNum) return;
    const currentMonth = today.getMonth() + 1;
    const year = currentMonth >= startNum ? today.getFullYear() : today.getFullYear() - 1;
    harvestPicker.min = `${year}-${pad(startNum)}-01`;
  }

  productSelect.addEventListener('change', () => {
    const hasProduct = !!productSelect.value;
    setProductLock(!hasProduct);
    if (!hasProduct) return;
    const base = getSelectedBasePrice();
    if (!isNaN(base)) {
      basePriceDisp.style.display = '';
      basePriceVal.textContent    = `£${base.toFixed(2)}`;
    } else {
      basePriceDisp.style.display = 'none';
    }
    updateSuggestedPrice();
    updateHarvestDateBounds();
  });

  setProductLock(true);

  document.querySelectorAll('input[name="quality_class"]').forEach(r => {
    r.addEventListener('change', updateSuggestedPrice);
  });

  function updateDiscountRow() {
    const qc = document.querySelector('input[name="quality_class"]:checked')?.value;
    document.getElementById('discount-row').style.display = qc === 'Discounted' ? '' : 'none';
  }
  document.querySelectorAll('input[name="quality_class"]').forEach(r => {
    r.addEventListener('change', updateDiscountRow);
  });
  updateDiscountRow();

  lockSeasonEnd('np-season-start', 'np-season-end');

  const formType = window.INVENTORY_CONFIG?.activeTab ?? 'new';
  if (formType === 'new_batch') switchTab('batch');
