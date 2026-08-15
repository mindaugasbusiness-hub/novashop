const products = [
  { id: 1, name: 'AirPods Pro', category: 'tech', price: 179.9, emoji: '🎧', rating: 4.9, badge: 'Nauja', stock: 12, sold: 19 },
  { id: 2, name: 'Tesla šviesos juosta', category: 'home', price: 49.0, emoji: '💡', rating: 4.8, badge: 'Populiaru', stock: 8, sold: 27 },
  { id: 3, name: 'Pilates kamuolys', category: 'sport', price: 24.5, emoji: '🏋️', rating: 4.7, badge: 'Rinktis', stock: 16, sold: 12 },
  { id: 4, name: '4K monitorius', category: 'tech', price: 299.0, emoji: '🖥️', rating: 4.9, badge: 'Top', stock: 5, sold: 18 },
  { id: 5, name: 'Bėgimo bateliai', category: 'sport', price: 89.0, emoji: '👟', rating: 4.8, badge: 'Naujiena', stock: 9, sold: 14 },
  { id: 6, name: 'Lauko kėdė', category: 'home', price: 129.0, emoji: '🪑', rating: 4.6, badge: 'SAVO', stock: 4, sold: 20 },
  { id: 7, name: 'Smart watch', category: 'tech', price: 159.0, emoji: '⌚', rating: 4.9, badge: 'Parduodama', stock: 7, sold: 31 },
  { id: 8, name: 'Joga kilimėlis', category: 'sport', price: 18.0, emoji: '🧘', rating: 4.5, badge: 'Lenktynės', stock: 22, sold: 8 }
];

const shipping = 3.99;
const cart = new Map();
const activeFilter = { value: 'all' };

const productsGrid = document.getElementById('products-grid');
const inventoryGrid = document.getElementById('inventory-grid');
const cartItemsEl = document.getElementById('cart-items');
const cartCountEl = document.getElementById('cart-count');
const subtotalEl = document.getElementById('subtotal');
const shippingEl = document.getElementById('shipping');
const totalEl = document.getElementById('total');
const cartPanel = document.getElementById('cart-panel');
const cartToggle = document.getElementById('cart-toggle');
const cartClose = document.getElementById('cart-close');
const checkoutForm = document.getElementById('checkout-form');
const statusEl = document.getElementById('status');
const filterButtons = [...document.querySelectorAll('.filter-btn')];
const featuredBtn = document.getElementById('featured-btn');

function formatCurrency(value) {
  return `€${value.toFixed(2)}`;
}

function getFilteredProducts() {
  return activeFilter.value === 'all'
    ? products
    : products.filter((product) => product.category === activeFilter.value);
}

function getAvailableStock(productId) {
  const product = products.find((item) => item.id === Number(productId));
  if (!product) return 0;
  return Math.max(0, product.stock - (cart.get(productId) || 0));
}

function renderProducts() {
  const visibleProducts = getFilteredProducts();

  productsGrid.innerHTML = visibleProducts
    .map((product) => {
      const available = Math.max(0, product.stock);
      const disabled = available <= 0 ? 'disabled' : '';
      const stockLabel = available <= 0 ? 'Išparduota' : `Likęs: ${available} vnt.`;

      return `
        <article class="product-card">
          <div class="product-visual">
            <span class="badge">${product.badge}</span>
            <span aria-hidden="true">${product.emoji}</span>
          </div>
          <div class="product-body">
            <div class="product-top">
              <div>
                <div class="product-category">${product.category}</div>
                <h3>${product.name}</h3>
              </div>
            </div>
            <p class="product-price">${formatCurrency(product.price)}</p>
            <p class="stock-status ${available <= 0 ? 'stock-empty' : available <= 5 ? 'stock-low' : 'stock-ok'}">${stockLabel}</p>

            <div class="product-meta">
              <span class="product-rating">★ ${product.rating}</span>
              <button class="product-btn ${disabled}" type="button" data-product-id="${product.id}" ${available <= 0 ? 'disabled' : ''}>Į krepšelį</button>
            </div>
          </div>
        </article>
      `;
    })
    .join('');
}

function renderInventory() {
  inventoryGrid.innerHTML = products
    .map((product) => {
      const remaining = product.stock;
      const stockClass = remaining <= 5 ? 'inventory-stock-low' : 'inventory-stock-ok';

      return `
        <div class="inventory-card">
          <h3>${product.name}</h3>
          <div class="inventory-metrics">
            <span>Likutis: <strong class="${stockClass}">${remaining} vnt.</strong></span>
            <span>Parduota: <strong>${product.sold} vnt.</strong></span>
            <span>Kategorija: <strong>${product.category}</strong></span>
          </div>
        </div>
      `;
    })
    .join('');
}

function getSubtotal() {
  let sum = 0;

  for (const [id, qty] of cart) {
    const product = products.find((item) => item.id === Number(id));
    if (product) sum += product.price * qty;
  }

  return sum;
}

function renderCart() {
  const entries = [...cart.entries()];

  if (entries.length === 0) {
    cartItemsEl.innerHTML = '<li class="empty-cart">Krepšelis tuščias</li>';
  } else {
    cartItemsEl.innerHTML = entries
      .map(([id, qty]) => {
        const product = products.find((item) => item.id === Number(id));
        if (!product) return '';

        return `
          <li class="cart-item">
            <span class="cart-item-name">${product.name}</span>
            <div class="qty-controls">
              <button class="qty-btn" type="button" data-action="dec" data-id="${id}">-</button>
              <span>${qty}</span>
              <button class="qty-btn" type="button" data-action="inc" data-id="${id}">+</button>
            </div>
            <strong>${formatCurrency(product.price * qty)}</strong>
          </li>
        `;
      })
      .join('');
  }

  const subtotal = getSubtotal();
  const delivery = subtotal > 0 ? (subtotal >= 75 ? 0 : shipping) : 0;
  const total = subtotal + delivery;

  subtotalEl.textContent = formatCurrency(subtotal);
  shippingEl.textContent = formatCurrency(delivery);
  totalEl.textContent = formatCurrency(total);
  cartCountEl.textContent = entries.reduce((sum, [, qty]) => sum + qty, 0);
}

function addToCart(productId) {
  const product = products.find((item) => item.id === Number(productId));
  if (!product) return;

  const inCart = cart.get(productId) || 0;
  if (product.stock <= inCart) {
    statusEl.textContent = `Prekė „${product.name}“ neturi laisvų vienetų.`;
    return;
  }

  cart.set(productId, inCart + 1);
  renderCart();
  renderProducts();
  renderInventory();
  statusEl.textContent = 'Prekė pridėta į krepšelį.';
  cartPanel.classList.add('open');
}

function updateQty(productId, delta) {
  const product = products.find((item) => item.id === Number(productId));
  if (!product) return;

  const current = cart.get(productId) || 0;
  const next = current + delta;

  if (next <= 0) {
    cart.delete(productId);
  } else if (next <= product.stock) {
    cart.set(productId, next);
  } else {
    statusEl.textContent = `Daugiau „${product.name}“ nei likutis sandėlyje.`;
    return;
  }

  renderCart();
  renderProducts();
  renderInventory();
}

productsGrid.addEventListener('click', (event) => {
  const button = event.target.closest('[data-product-id]');
  if (!button) return;
  addToCart(Number(button.dataset.productId));
});

cartItemsEl.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action][data-id]');
  if (!button) return;

  const id = Number(button.dataset.id);
  const action = button.dataset.action;
  updateQty(id, action === 'inc' ? 1 : -1);
});

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    activeFilter.value = button.dataset.filter;
    filterButtons.forEach((btn) => btn.classList.toggle('active', btn === button));
    renderProducts();
  });
});

cartToggle.addEventListener('click', () => {
  cartPanel.classList.add('open');
});

cartClose.addEventListener('click', () => {
  cartPanel.classList.remove('open');
});

featuredBtn.addEventListener('click', () => {
  document.getElementById('featured').scrollIntoView({ behavior: 'smooth' });
});

checkoutForm.addEventListener('submit', (event) => {
  event.preventDefault();

  if (cart.size === 0) {
    statusEl.textContent = 'Pirmiausia pridėkite prekių į krepšelį.';
    return;
  }

  const formData = new FormData(checkoutForm);
  const name = formData.get('name') || 'Klientas';

  for (const [productId, qty] of cart.entries()) {
    const product = products.find((item) => item.id === Number(productId));
    if (!product) continue;
    product.stock = Math.max(0, product.stock - qty);
    product.sold += qty;
  }

  cart.clear();
  renderProducts();
  renderCart();
  renderInventory();
  checkoutForm.reset();
  statusEl.textContent = `Ačiū, ${name}! Užsakymas gautas demo režimu.`;
});

renderProducts();
renderInventory();
renderCart();
