// Management panel: Script to lazily load order details for expanded order summary
const buttons = document.querySelectorAll('.js-load-order-summary');
modal_div = document.getElementById('orderSummaryModal');
const modal = new bootstrap.Modal(modal_div);

const STATUS_PROGRESS_MAP = { PENDING: 25, CONFIRMED: 50, READY: 75, DELIVERED: 100 };
const STATUS_ICON_MAP = {
    READY:     '<i class="bi bi-clock ms-1"></i>',
    DELIVERED: '<i class="bi bi-check2-circle ms-1"></i>',
    CANCELLED: '<i class="bi bi-x-circle ms-1"></i>',
};

document.querySelectorAll('.order-summary-row input, .order-summary-row select, .order-summary-row textarea, .order-summary-row button:not(.js-load-order-summary)')
    .forEach(el => el.addEventListener('click', e => e.stopPropagation()));

const pill = (s, sm = false) =>
    `<span class="status-pill${sm ? ' status-pill-sm' : ''} ms-1 status-pill-${s.toLowerCase()}">${s}${STATUS_ICON_MAP[s] || ''}</span>`;

function buildReceiptTable(receipt, canAdvance, showProducerCol) {
    if (!receipt.length) return '<p class="text-muted">No items.</p>';
    const producerCol = showProducerCol ? '<th>Producer</th>' : '';
    const colSpan = showProducerCol ? 7 : 6;
    let html = `<table class="table table-sm table-bordered table-hover table-striped">
        <thead class="table-light"><tr>
            ${producerCol}
        <th>Item</th><th>Grade</th><th>Best Before</th>
            <th class="text-center">Qty</th>
            <th class="text-end">Stock</th>
            <th class="text-end">Unit Price</th>
            <th class="text-end">Line Total</th>
        </tr></thead><tbody>`;
    let grandTotal = 0;
    receipt.forEach(item => {
        const afterClass = item.stock_after < 0 ? 'text-success' : item.stock_after === 0 ? 'text-danger' : '';
        const stockCell = canAdvance
            ? `<td class="text-end">${item.stock_now} <i class="bi bi-arrow-right text-muted"></i> <span class="${afterClass}">${item.stock_after}</span></td>`
            : '<td class="text-end text-muted">N/A</td>';
        const batchUrl = `/management/?model=ProductBatch&q=${encodeURIComponent(item.batch_number)}`;
        grandTotal += parseFloat(item.total);
        html += `<tr style="cursor:pointer" onclick="window.open('${batchUrl}','_blank')" title="Open batch">
            ${showProducerCol ? `<td><small class="text-muted">${item.producer || '-'}</small></td>` : ''}
        <td>${item.name} <small class="text-muted">${item.batch_number}</small></td>
            <td><span class=" text-success">${item.quality_class}</span></td>
            <td class="text-muted">${item.best_before || '-'}</td>
            <td class="text-center">${item.qty}</td>
            ${stockCell}
            <td class="text-end text-success">£${item.price}</td>
            <td class="text-end text-success">£${item.total}</td>
        </tr>`;
    });
    html += `<tr class="table-light fw-bold">
        <td colspan="${colSpan}" class="text-end text-uppercase">Total</td>
        <td class="text-end text-success">£${grandTotal.toFixed(2)}</td>
    </tr></tbody></table>`;
    return html;
}

function buildProducerOrdersSection(producerOrders) {
    if (!producerOrders || !producerOrders.length) return '';
    return producerOrders.map((po, i) => {
        const advBtn = po.advance_url
            ? `<div class="mt-2">
                <textarea class="form-control form-control-sm mb-1" id="po-note-${i}" rows="2" placeholder="Optional note..."></textarea>
                <button class="btn btn-sm btn-outline-success w-100 po-advance-btn"
                    data-url="${po.advance_url}" data-note-id="po-note-${i}">
                    Advance to ${po.next_status}
                </button>
               </div>`
            : '';
        return `<div class="border rounded p-2 mb-2">
            <div class="d-flex align-items-center gap-2 flex-wrap">
                <strong style="font-size:.85rem">${po.producer}</strong>
                ${pill(po.status, true)}
                <span class="text-muted" style="font-size:.8rem">Delivery: ${po.delivery_date || 'N/A'}</span>
            </div>
            ${advBtn}
        </div>`;
    }).join('');
}

function buildHistoryTimeline(history) {
    if (!history || !history.length) return '<p class="text-muted" style="font-size:.82rem">No history yet.</p>';
    return history.map(h => `
        <div class="d-flex gap-2 mb-1 align-items-center flex-wrap" style="font-size:.82rem">
            ${pill(h.from, true)}
            <i class="bi bi-arrow-right text-muted"></i>
            ${pill(h.to, true)}
            <span class="text-muted">${h.at}</span>
            ${h.note ? `<span class="fst-italic text-muted">"${h.note}"</span>` : ''}
        </div>`).join('');
}

buttons.forEach(button => {
    button.addEventListener('click', function () {
        const orderId = this.getAttribute('order-row-id');
        modal.show();
        document.getElementById('order-id').innerText = orderId;
        document.getElementById('customer_name').innerText = 'Loading...';
        document.getElementById('receipt-table').innerHTML = '<p class="text-muted p-3">Loading...</p>';
        document.getElementById('error').innerText = '';
        document.getElementById('advance-section').classList.add('d-none');
        document.getElementById('producer-orders-section').style.display = 'none';
        document.getElementById('producer-orders-list').innerHTML = '';

        fetch(`/management/order/${orderId}/order_summary/`)
            .then(r => r.json())
            .then(data => {
                if (data.error) { document.getElementById('error').innerText = `Error: ${data.error}`; return; }

                // Header fields
                ['customer_name','customer_type','email','phone','address',
                 'order_date','delivery_date','recurrence','instructions'].forEach(key => {
                    const el = document.getElementById(key);
                    if (el) el.innerText = data[key] || 'Not provided';
                });
                const totalEl = document.getElementById('total_price');
                if (totalEl) totalEl.innerText = `£${data.total_price}`;

                // Overall status pill
                const statusEl = document.getElementById('status');
                statusEl.innerHTML = data.status + (STATUS_ICON_MAP[data.status] || '');
                statusEl.className = `status-pill ms-2 status-pill-${data.status.toLowerCase()}`;

                // Progress bar (overall)
                const progressBar = document.getElementById('order-progress-bar');
                if (data.status === 'CANCELLED') {
                    progressBar.style.width = '100%';
                    progressBar.className = 'progress-bar bg-danger';
                    progressBar.innerText = 'CANCELLED';
                } else {
                    const percent = STATUS_PROGRESS_MAP[data.status] || 0;
                    const cls = data.status.toLowerCase();
                    setTimeout(() => { progressBar.style.width = `${percent}%`; }, 50);
                    progressBar.className = `progress-bar bg-${cls} progress-bar-striped progress-bar-animated`;
                    progressBar.innerText = `${percent}%`;
                    ['PENDING','CONFIRMED','READY','DELIVERED'].forEach(stage => {
                        const lbl = document.getElementById(`label-${stage}`);
                        lbl.className = stage === data.status ? `text-${stage.toLowerCase()}` : 'text-muted';
                    });
                }

                const csrf = document.querySelector('[name="csrfmiddlewaretoken"]').value;
                const canAdvance = data.producer_orders
                    ? data.producer_orders.some(po => po.advance_url)
                    : !!data.advance_url;

                // Receipt and history
                document.getElementById('receipt-table').innerHTML =
                    buildReceiptTable(data.receipt, canAdvance, data.show_producer_col);
                document.getElementById('status-history').innerHTML =
                    buildHistoryTimeline(data.status_history);

                // Embedded producer orders section (superuser only)
                const poSection = document.getElementById('producer-orders-section');
                const poList = document.getElementById('producer-orders-list');
                if (data.producer_orders && data.producer_orders.length) {
                    poList.innerHTML = buildProducerOrdersSection(data.producer_orders);
                    poSection.style.display = '';
                    poList.querySelectorAll('.po-advance-btn').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const note = document.getElementById(btn.dataset.noteId).value;
                            fetch(btn.dataset.url, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                                body: new URLSearchParams({ csrfmiddlewaretoken: csrf, note }),
                            }).then(() => { modal.hide(); window.location.reload(); });
                        });
                    });
                } else {
                    poSection.style.display = 'none';
                }

                // Single advance section (producer only)
                const advSection = document.getElementById('advance-section');
                if (!data.producer_orders && data.advance_url && data.next_status) {
                    advSection.classList.remove('d-none');
                    document.getElementById('advance-label').innerText = `Advance to ${data.next_status}`;
                    const advBtn = document.getElementById('advance-btn');
                    advBtn.innerText = `Advance to ${data.next_status}`;
                    const fresh = advBtn.cloneNode(true);
                    advBtn.parentNode.replaceChild(fresh, advBtn);
                    fresh.addEventListener('click', () => {
                        const note = document.getElementById('advance-note').value;
                        fetch(data.advance_url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: new URLSearchParams({ csrfmiddlewaretoken: csrf, note }),
                        }).then(() => { modal.hide(); window.location.reload(); });
                    });
                } else if (data.producer_orders) {
                    advSection.classList.add('d-none');
                }
            });
    });
});
