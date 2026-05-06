// Management panel: Script to lazily load order details for expanded order summary
const buttons = document.querySelectorAll('.js-load-order-summary');
modal_div = document.getElementById('orderSummaryModal');
const modal = new bootstrap.Modal(modal_div);

const STATUS_PROGRESS_MAP = {
    'PENDING': 25,
    'CONFIRMED': 50,
    'READY': 75,
    'DELIVERED': 100
};

// Prevent row click from firing when interacting with form elements inside the row
document.querySelectorAll('.order-summary-row input, .order-summary-row select, .order-summary-row textarea, .order-summary-row button:not(.js-load-order-summary)')
    .forEach(el => el.addEventListener('click', e => e.stopPropagation()));

const STATUS_ICON_MAP = {
    READY:     '<i class="bi bi-clock ms-1"></i>',
    DELIVERED: '<i class="bi bi-check2-circle ms-1"></i>',
    CANCELLED: '<i class="bi bi-x-circle ms-1"></i>',
};

// statusEl.className = `status-pill ms-2 status-pill-${data.status.toLowerCase()}`;
const pill = s => `<span class="status-pill ms-2 status-pill-${s.toLowerCase()}" style="padding: 0.25em; margin: 0.25em; font-size: 0.85em;">${s}${STATUS_ICON_MAP[s]||''}</span>`;

buttons.forEach(button => {
    button.addEventListener('click', function () {
        const orderId = this.getAttribute('order-row-id');

        modal.show();
        document.getElementById('order-id').innerText = orderId;
        document.getElementById('customer_name').innerText = 'Loading...';
        document.getElementById('receipt-table').innerHTML = 'Loading items...';
        document.getElementById('advance-section').classList.add('d-none');

        fetch(`/management/order/${orderId}/order_summary/`)
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('error').innerText = `Error: ${data.error}`;
                    return;
                }

                // Populate simple text fields
                ['customer_name','customer_type','email','phone','address',
                 'order_date','delivery_date','recurrence','instructions','total_price'].forEach(key => {
                    const el = document.getElementById(key);
                    if (el) el.innerText = data[key] || 'Not provided';
                });

                // Status pill in header
                const statusEl = document.getElementById('status');
                const iconHtml = STATUS_ICON_MAP[data.status] ? STATUS_ICON_MAP[data.status] : '';
                statusEl.innerHTML = data.status + iconHtml;
                statusEl.className = `status-pill ms-2 status-pill-${data.status.toLowerCase()}`;

                // Receipt table with stock columns
                const list = document.getElementById('receipt-table');
                if (!data.receipt.length) {
                    list.innerHTML = 'No products attached to this order.';
                } else {

                    
                    const showStock = data.next_status !== null;
                    const producerCol = data.show_producer_col;
                    const producerTh = producerCol ? `<th>Producer</th>` : '';
                    const totalColspan = producerCol ? 7 : 6;
                    let html = `<table class="table table  table-bordered table-striped">
                        <thead class="table-light"><tr>
                            ${producerTh}
                        <th>Item</th>
                            <th>Grade</th>
                            <th>Best Before</th>
                            <th class="text-center">Quantity</th>
                            <th class="text-end">Current Stock</th>
                            <th class="text-end">Unit Price</th>
                            <th class="text-end">Line Total</th>
                            </tr>
                            </thead>
                            <tbody class="align-middle">`;
                    data.receipt.forEach(item => {
                        const stockAfterClass = item.stock_after < 0 ? 'text-danger fw-bold' : item.stock_after === 0 ? 'text-warning' : '';
                        const stockCells = showStock
                            ? `<td class="text-end text-success">${item.stock_now} <span class="text-black"><i class="bi bi-arrow-right"></i></span>
                            <span class="text-end ${stockAfterClass}">${item.stock_after}</span></td>`
                            : '<td class="text-end">N/A</td>';
                        const producerTd = producerCol ? `<td class="text-muted" style="font-size:.8rem;">${item.producer || '—'}</td>` : '';
                        const batchUrl = `/management/?model=ProductBatch&q=${encodeURIComponent(item.batch_number)}`;
                        html += `<tr style="cursor:pointer;" onclick="window.open('${batchUrl}', '_blank')" title="Open batch ${item.batch_number} in management">
                                                    ${producerTd}
    
                        <td>${item.name} <small class="text-muted" style="font-size:.8rem;">${item.batch_number}</small></td>
                            <td><span class="badge bg-success text-white">${item.quality_class}</span></td>
                            <td class="text-muted" style="font-size:.8rem;">${item.best_before || '—'}</td>
                            <td class="text-center">${item.qty}</td>
                            ${stockCells}
                            <td class="text-end text-success">£${item.price}</td>
                            <td class="text-end text-success">£${item.total}</td>
                        </tr>`;
                    });
                    const displayTotal = data.visible_total;
                    html += `
                        <tr class="table-light fw-bold">
                            <td colspan="${totalColspan}" class="text-end text-uppercase">Total</td>
                            <td class="text-end text-success">£${displayTotal}</td>
                        </tr>
                    `;
                    html += '</tbody></table>';
                    list.innerHTML = html;
                }

                // Status history timeline
                
                const historyEl = document.getElementById('status-history');
                if (data.status_history && data.status_history.length) {
                    historyEl.innerHTML = data.status_history.map(h => `
                        <div class="d-flex gap-2 mb-2 align-items-center flex-wrap">
                            ${pill(h.from)}
                            <i class="bi bi-arrow-right text-muted"></i>
                            ${pill(h.to)}
                            <span class="text-muted">${h.at}</span>
                            ${h.note ? `<span class="fst-italic text-muted">${h.note}</span>` : ''}
                        </div>`).join('');
                } 

                // Update Progress Bar
                const progressBar = document.getElementById('order-progress-bar');
                const progressContainer = document.getElementById('progress-container');
                
                if (data.status === 'CANCELLED') {
                    // Handle cancelled state elegantly
                    progressBar.style.width = '100%';
                    progressBar.className = 'progress-bar bg-danger';
                    progressBar.innerText = 'CANCELLED';
                } else {
                    // Normal linear progression
                    const percent = STATUS_PROGRESS_MAP[data.status] || 0;
                    
                    // Convert "CONFIRMED" to "confirmed" so it matches your CSS classes perfectly
                    const statusClass = data.status.toLowerCase(); 
                    
                    setTimeout(() => {
                        progressBar.style.width = `${percent}%`;
                    }, 50);
                    
                    // Inject your custom 'bg-{status}' class!
                    progressBar.className = `progress-bar bg-${statusClass} progress-bar-striped progress-bar-animated`;
                    progressBar.innerText = `${percent}%`;
                    
                    // Highlight the current text label e
                    ['PENDING', 'CONFIRMED', 'READY', 'DELIVERED'].forEach(stage => {
                        const labelEl = document.getElementById(`label-${stage}`);
                        const stageClass = stage.toLowerCase();
                        
                        // Strip out all potential custom text colors first
                        labelEl.classList.remove('text-muted', 'text-pending', 'text-confirmed', 'text-ready', 'text-delivered');
                        
                        if (stage === data.status) {
                            labelEl.classList.add(`text-${stageClass}`); // Add your custom color
                        } else {
                            labelEl.classList.add('text-muted'); // Gray out the rest
                        }
                    });
                }
                    

                // Advance section — only shown for PENDING / CONFIRMED
                if (data.advance_url && data.next_status) {
                    const section = document.getElementById('advance-section');

                    document.getElementById('advance-label').innerHTML =
                        `Advance to ${pill(data.next_status)} `;
                    const advanceBtn = document.getElementById('advance-btn');
                    advanceBtn.innerHTML = `Advance to ${data.next_status} <i class="bi bi-arrow-right"></i>`;
                    document.getElementById('advance-note').value = '';

                    document.getElementById('advance-btn').onclick = () => {
                        const note = document.getElementById('advance-note').value;
                        const csrf = document.querySelector('[name="csrfmiddlewaretoken"]').value;
                        fetch(data.advance_url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                            body: new URLSearchParams({ csrfmiddlewaretoken: csrf, note }),
                        }).then(() => { modal.hide(); window.location.reload(); });
                    };
                    section.classList.remove('d-none');
                }
            });
    });
});
