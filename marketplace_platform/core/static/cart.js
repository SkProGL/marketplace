function addToCart(productId, btn) {
  fetch(`/cart/update/${productId}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute("content"),
    },
    body: JSON.stringify({ delta: 1 }),
  })
    .then((r) => {
      if (r.redirected || r.status === 403) {
        window.location.href = "/login/";
        return null;
      }
      return r.json();
    })
    .then((data) => {
      if (!data) return;
      updateDrawerIfOpen(data);
      // Swap button for stepper
      const widget = btn.closest(".cart-widget");
      widget.innerHTML = `
            <div class="cart-stepper">
                <button class="widget-stepper-btn" onclick="updateCart('${productId}', -1, this)">−</button>
                <span class="stepper-qty">${data.quantity}</span>
                <button class="widget-stepper-btn" onclick="updateCart('${productId}', 1, this)">+</button>
            </div>`;
      updateNavbarCart(data.total_items, data.total_price);
    });
}

function updateCart(productId, delta, btn) {
  fetch(`/cart/update/${productId}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute("content"),
    },
    body: JSON.stringify({ delta: delta }),
  })
    .then((r) => {
      if (r.redirected || r.status === 403) {
        window.location.href = "/login/";
        return null;
      }
      return r.json();
    })
    .then((data) => {
      if (!data) return;
      updateDrawerIfOpen(data);
      const widget = btn.closest(".cart-widget");
      if (data.quantity <= 0) {
        // Swap back to Add button
        widget.innerHTML = `<button class="add-to-cart-btn" onclick="addToCart('${productId}', this)">Add</button>`;
      } else {
        widget.querySelector(".stepper-qty").innerText = data.quantity;
      }
      updateNavbarCart(data.total_items, data.total_price);
    });
}

function updateNavbarCart(totalItems, totalPrice) {
  const bubble = document.querySelector(".cart-bubble span");
  const parent = document.querySelector("#base-cart");
  if (bubble && parseFloat(totalPrice) === 0) {
    parent.classList.remove("empty");
    bubble.innerText = "";
  } else {
    parent.classList.add("empty");
    bubble.innerText = "£" + parseFloat(totalPrice).toFixed(2);
  }
}
function openCart() {
  fetch("/cart/contents/")
    .then((r) => r.json())
    .then((data) => {
      updateDrawerIfOpen(data);
      renderDrawer(data);
      document.getElementById("cartDrawer").classList.add("open");
      document.getElementById("cartOverlay").classList.add("active");
    });
}

function closeCart() {
  document.getElementById("cartDrawer").classList.remove("open");
  document.getElementById("cartOverlay").classList.remove("active");
}

function renderDrawer(data) {
  const itemsEl = document.getElementById("cartDrawerItems");
  const footerEl = document.getElementById("cartDrawerFooter");
  const totalEl = document.getElementById("cartDrawerTotal");

  if (!data.cart_items || data.cart_items.length === 0) {
    itemsEl.innerHTML = '<p class="cart-empty-msg">Your cart is empty</p>';
    footerEl.style.display = "none";
    return;
  }

  // Group items by producer
  const groups = {};
  const groupOrder = [];
  data.cart_items.forEach(item => {
    const key = item.producer_id || 'unknown';
    if (!groups[key]) { groups[key] = { name: item.producer || 'Producer', items: [] }; groupOrder.push(key); }
    groups[key].items.push(item);
  });

  itemsEl.innerHTML = groupOrder.map(key => {
    const group = groups[key];
    const itemsHtml = group.items.map(item => `
      <div class="cart-drawer-item">
          ${item.image
            ? `<img src="${item.image}" alt="${item.name}">`
            : `<div style="width:50px;height:50px;background:#f0f0f0;border-radius:6px;"></div>`}
          <div class="cart-drawer-item-info">
              <div class="cart-drawer-item-name">${item.name}</div>
              <div class="cart-drawer-item-qty">£${item.price.toFixed(2)} each</div>
          </div>
          <div class="cart-drawer-stepper">
              <button class="widget-stepper-btn" onclick="drawerUpdateCart('${item.id}', -1, this)">−</button>
              <span class="stepper-qty">${item.quantity}</span>
              <button class="widget-stepper-btn" onclick="drawerUpdateCart('${item.id}', 1, this)">+</button>
          </div>
          <span class="cart-drawer-item-price">£${item.subtotal.toFixed(2)}</span>
      </div>`).join('');
    return `
      <div class="cart-producer-group">
          <div class="cart-producer-label">${group.name}</div>
          ${itemsHtml}
      </div>`;
  }).join('');

  totalEl.innerText = `£${data.total_price.toFixed(2)}`;
  footerEl.style.display = "flex";
}

// Update drawer if it's open when cart changes
function updateDrawerIfOpen(data) {
  if (document.getElementById("cartDrawer").classList.contains("open")) {
    renderDrawer(data);
  }
}
function drawerUpdateCart(productId, delta, btn) {
  fetch(`/cart/update/${productId}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document
        .querySelector('meta[name="csrf-token"]')
        .getAttribute("content"),
    },
    body: JSON.stringify({ delta: delta }),
  })
    .then((r) => r.json())
    .then((data) => {
      renderDrawer(data);
      updateNavbarCart(data.total_items, data.total_price);

      // Sync cartState and card badge on the home page if available
      if (typeof cartState !== "undefined") {
        if (data.quantity <= 0) {
          delete cartState[productId];
        } else {
          cartState[productId] = data.quantity;
        }
        if (typeof batchData !== "undefined" && typeof updateCardCartBadge === "function") {
          for (const [pid, batches] of Object.entries(batchData)) {
            if (batches.some((b) => b.id === productId)) {
              updateCardCartBadge(pid);
              break;
            }
          }
        }
      }
    });
}

function syncCardWidget(productId, quantity) {
  const card = document.querySelector(
    `.cart-widget[data-product-id="${productId}"]`,
  );
  if (!card) return;
  if (quantity <= 0) {
    card.innerHTML = `<button class="add-to-cart-btn" onclick="addToCart('${productId}', this)">Add</button>`;
  } else {
    const qty = card.querySelector(".stepper-qty");
    if (qty) qty.innerText = quantity;
  }
}
