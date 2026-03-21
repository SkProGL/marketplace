// Management panel: Script to lazily load order details for expanded order summary
const buttons = document.querySelectorAll('.load-receipt-btn');
const modal = new bootstrap.Modal(document.getElementById('receiptModal'));

buttons.forEach(button => {
    button.addEventListener('click', function () {
        const orderId = this.getAttribute('data-order-id');

        modal.show();
        document.getElementById('modal-order-id').innerText = orderId;
        document.getElementById('modal-customer-name').innerText = "Loading...";
        document.getElementById('modal-receipt-table').innerHTML = "<li>Loading items...</li>";

        fetch(`/management/order/${orderId}/receipt/`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('modal-status').innerText = data.status || 'Not provided';;
                document.getElementById('modal-customer-name').innerText = data.customer_name || 'Not provided';;
                document.getElementById('modal-customer-type').innerText = data.customer_type || 'Not provided';;
                document.getElementById('modal-email').innerText = data.email || 'Not provided';
                document.getElementById('modal-phone').innerText = data.phone || 'Not provided';
                document.getElementById('modal-address').innerText = data.address || 'Not provided';
                document.getElementById('modal-instructions').innerText = data.instructions || 'Not provided';;
                document.getElementById('modal-order-date').innerText = data.order_date || 'Not provided';
                document.getElementById('modal-delivery-date').innerText = data.delivery_date || 'Not provided';
                document.getElementById('modal-recurrence').innerText = data.recurrence || 'Not provided';
                document.getElementById('modal-total').innerText = data.total_price || 'Not provided';

                // Populate the list
                const list = document.getElementById('modal-receipt-table');
                list.innerHTML = "";
                if (data.receipt.length === 0) {
                    list.innerHTML = "No items attached to this order yet.";
                } else {
                    let tableHTML = `
                        <table class="table table-sm table-bordered">
                            <thead class="table-light">
                                <tr>
                                    <th>Item</th>
                                    <th class="text-center">Qty</th>
                                    <th class="text-end">Unit Price</th>
                                    <th class="text-end">Line Total</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;
                    data.receipt.forEach(item => {
                        tableHTML += `
                            <tr>
                                <td>${item.name}</td>
                                <td class="text-center">${item.qty}</td>
                                <td class="text-end">£${item.price}</td>
                                <td class="text-end">£${item.total}</td>
                            </tr>
                    `;
                    });

                    tableHTML += `
                    </tbody>
                </table>
            `;

                    // Inject the finished HTML into the modal
                    list.innerHTML = tableHTML;
                }
            });
    });
});

