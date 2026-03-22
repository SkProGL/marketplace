// Management panel: Script to lazily load order details for expanded order summary
//  Select load summary buttons
const buttons = document.querySelectorAll('.js-load-order-summary');
// Get modal div
modal_div = document.getElementById('orderSummaryModal')
// Create modal object
const modal = new bootstrap.Modal(modal_div);

// Assign click event listener and callback to each button
buttons.forEach(button => {
    button.addEventListener('click', function () {
        // Define callback
        // Extract row id from selected button element selected
        const orderId = this.getAttribute('order-row-id');
        
        // Disply modal and placeholder data
        modal.show();
        document.getElementById('order-id').innerText = orderId;
        document.getElementById('customer_name').innerText = "Loading...";
        document.getElementById('receipt-table').innerHTML = "Loading items...";

        // Async GET request using orderId as argument for display data
        // waits for JSON response
        fetch(`/management/order/${orderId}/order_summary/`)
            .then(response => response.json()) // Get HTTP response
            .then(data => { // Parse JSON body and pass details to modal template
                if (data.error) {
                    document.getElementById('error').innerText = `Error: ${data.error}`;
                    return;
                }
                Object.keys(data).forEach(key => {
                    const element = document.getElementById(key);
                    console.log(element)
                    if (element) element.innerText = data[key] || 'Not provided';
                });
                // Set status badge colour based on status
                const status = document.getElementById('status');
                status.innerText = data.status;
                status.className = `badge ms-2 ${
                    // JS inline if-else
                    data.status === 'PENDING'   ? 'bg-warning'  :
                    data.status === 'CONFIRMED' ? 'bg-primary'  :
                    data.status === 'DELIVERED' ? 'bg-success'  : 
                    'bg-danger'
                }`;

                // Construct itemised receipt table
                const list = document.getElementById('receipt-table');
                list.innerHTML = "";
                if (data.receipt.length === 0) {
                    list.innerHTML = "No products attached to this order.";
                } else {
                    let tableHTML = `
                        <table class="table table-sm table-bordered table-striped">
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
                    </table> `;
                    // Inject the HTML into the modal
                    list.innerHTML = tableHTML;
                }
            });
    });
});

