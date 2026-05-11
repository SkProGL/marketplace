// Standalone grade-modal renderer. Mirrors the modal behaviour in
// inventory_upload.js so the manager dispute page can reuse the same UI
// against a persisted ai_evidence payload.

(function () {
  const GRADE_COLOURS = { A: '#1a7a3c', B: '#3a7abf', C: '#c97a00', D: '#c94000', Rejected: '#991111' };

  let _gmCurrent = null;

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
    const manualPanel = document.getElementById('gm-manual-panel');
    if (manualPanel) manualPanel.style.display = view === 'manual' ? '' : 'none';
    document.getElementById('gm-btn-basic').classList.toggle('active',    view === 'basic');
    document.getElementById('gm-btn-advanced').classList.toggle('active', view === 'advanced');
    const manualBtn = document.getElementById('gm-btn-manual');
    if (manualBtn) manualBtn.classList.toggle('active', view === 'manual');
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
      const ZONES = [
        { grade: 'D', lo: 0,  hi: 65, color: '#aaa' },
        { grade: 'C', lo: 65, hi: 75, color: '#e8a020' },
        { grade: 'B', lo: 75, hi: 85, color: '#3a7abf' },
        { grade: 'A', lo: 85, hi: 100, color: '#1a7a3c' },
      ];
      const thermometer = (() => {
        const score = Math.min(composite, 100);
        const ticks = [65, 75, 85].map(t =>
          `<div style="position:absolute;left:${t}%;top:0;height:100%;width:1px;background:rgba(0,0,0,0.18);"></div>
           <div style="position:absolute;left:${t}%;top:-14px;font-size:0.62rem;color:#999;transform:translateX(-50%);">${t}</div>`
        ).join('');
        const fills = ZONES.map(z => {
          const w = z.hi - z.lo;
          return `<div style="position:absolute;left:${z.lo}%;width:${w}%;height:100%;background:${z.color};opacity:0.55;border-radius:${z.lo===0?'7px 0 0 7px':''}${z.hi===100?'0 7px 7px 0':''}"></div>`;
        }).join('');
        const labels = ZONES.map(z => {
          const mid = z.lo + (z.hi - z.lo) / 2;
          return `<div style="position:absolute;left:${mid}%;top:18px;font-size:0.72rem;color:${z.color};font-weight:800;transform:translateX(-50%);">${z.grade}</div>`;
        }).join('');
        const marker = `<div style="position:absolute;left:${score}%;top:-4px;bottom:-4px;width:4px;background:${gradeColor};border-radius:3px;transform:translateX(-50%);box-shadow:0 0 4px 1px ${gradeColor};z-index:2;"></div>`;
        return `<div style="position:relative;padding:18px 8px 32px;background:transparent;">
          <div style="position:relative;height:14px;background:#e8e8e8;border-radius:7px;overflow:visible;">${fills}${ticks}${marker}</div>
          <div style="position:relative;height:20px;">${labels}</div>
        </div>`;
      })();
      steps.push({
        title: '4 - Composite Grade',
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
        <table class="gm-formula-table">
          ${s.rows.map(([k, v, cls='']) => `<tr class="${cls==='total'?'gm-formula-row--total':''}"><td class="gm-fk">${k}</td><td class="gm-fv">${v}</td></tr>`).join('')}
        </table>
        ${s.thermometer ? s.thermometer : ''}
        ${s.note     ? `<p class="gm-formula-note">${s.note}</p>` : ''}
        ${s.noteInfo ? `<p style="margin:0;padding:6px 12px 8px;font-size:0.76rem;color:#555;background:#f5f8ff;border-top:1px solid #d0d8f0;">${s.noteInfo}</p>` : ''}
        ${s.img  ? `<div style="background:#f5f5f5;padding:6px 10px 10px;"><img src="data:image/png;base64,${s.img}" style="display:block;width:100%;border-radius:4px;border:1px solid #ddd;"></div>` : ''}
      </div>`).join('');
  }

  function openGradeModal(result, managerContext) {
    const r = result || _gmCurrent;
    if (!r) return;
    _gmCurrent = r;

    // Manager review tab: only visible when the caller supplies the context
    // (complaint id, action URL, csrf token). Inventory upload page omits it.
    const manualBtn = document.getElementById('gm-btn-manual');
    if (manualBtn) {
      if (managerContext) {
        manualBtn.style.display = '';
        document.getElementById('gm-manual-cid').value  = managerContext.complaintId || '';
        document.getElementById('gm-manual-csrf').value = managerContext.csrfToken || '';
        document.getElementById('gm-manual-form').action = managerContext.actionUrl || '';

        const aiGradeEl = document.getElementById('gm-manual-ai-grade');
        aiGradeEl.textContent = r.overall_grade || '-';
        aiGradeEl.style.color = GRADE_COLOURS[r.overall_grade] || '#333';

        const imgEl = document.getElementById('gm-manual-image');
        const naEl  = document.getElementById('gm-manual-image-na');
        if (r.input_image_b64) {
          imgEl.src = `data:image/jpeg;base64,${r.input_image_b64}`;
          imgEl.style.display = '';
          naEl.style.display = 'none';
        } else {
          imgEl.style.display = 'none';
          naEl.style.display = '';
        }

        const currentEl = document.getElementById('gm-manual-current');
        const currentVal = document.getElementById('gm-manual-current-val');
        if (managerContext.currentGrade) {
          currentEl.style.display = '';
          currentVal.textContent  = managerContext.currentGrade;
          currentVal.style.color  = GRADE_COLOURS[managerContext.currentGrade] || '#333';
          const preset = document.querySelector(`#gm-manual-form input[name="manager_grade"][value="${managerContext.currentGrade}"]`);
          if (preset) preset.checked = true;
        } else {
          currentEl.style.display = 'none';
          document.querySelectorAll('#gm-manual-form input[name="manager_grade"]').forEach(el => { el.checked = false; });
        }
      } else {
        manualBtn.style.display = 'none';
      }
    }

    const grade = r.overall_grade;
    const m = r.metrics || {};
    const exp = r.explanation || {};

    const badge = document.getElementById('gm-grade-badge');
    badge.textContent = grade;
    badge.style.color = GRADE_COLOURS[grade] || '#333';

    const summary = document.getElementById('gm-result-summary');
    summary.style.borderLeftColor = GRADE_COLOURS[grade] || '#ccc';
    summary.style.background = grade === 'Rejected' ? '#fff5f4' : '#f7f7f7';

    document.getElementById('gm-rejected-notice').style.display = grade === 'Rejected' ? '' : 'none';

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
      { label: 'Ripeness',   value: m.ripeness, decisive: true,                  note: 'Softmax confidence on health prediction' },
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

    const method = exp.method || 'unknown';
    const methodLabels = { mtl: 'Multi-task neural network (MTL)', stl: 'Single-task neural network (STL)', 'heuristic-pixel-rubric': 'Heuristic pixel fallback (no model loaded)' };
    document.getElementById('gm-method-note').textContent =
      `Inference method: ${methodLabels[method] || method}. Health confidence: ${exp.health_confidence != null ? exp.health_confidence.toFixed(1) + '%' : '-'}.`;

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

    document.getElementById('gm-formula-content').innerHTML = buildFormulaHtml(r);
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

  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeGradeModal(); });

  window.openGradeModal  = openGradeModal;
  window.closeGradeModal = closeGradeModal;
  window.switchGmView    = switchGmView;
  window.toggleMetric    = toggleMetric;
})();
