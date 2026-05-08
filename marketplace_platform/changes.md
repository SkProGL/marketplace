# Changes Log

## Frontend (Templates & Static)
### `base.html`
- **Navbar Refactoring:** 
  - Moved cart functionality to a fixed bottom-right button (`#cart-launcher`).
  - Removed cart link from navbar.
  - Replaced the single "Menu" dropdown with two distinct, icon-based dropdowns: **Manage** (Inventory, Management, Community, Orders, Finance) and **Account** (Profile, Logout).
  - Reordered navbar items to place Notifications before the dropdowns.
  - Refactored Login/Signup links into button-styled links.

### `home.html`
- **Filter Layout:**
  - Integrated the **Producer/Organization search** field (`#orgSearch`) and its associated dropdown (`#orgDropdown`) into the main filter row.
  - Realigned and grouped "Include categories", "In Stock", "Discounted", and "Organic" filters to be inline.
  - Cleaned up the "Exclude allergens" section by removing duplicates and keeping the "More/Less" toggle functionality.
- **JS Logic:**
  - Added `filterOrgs()` and `selectOrg()` JS functions to handle searching through producer organizations via an API.

### `base.css`
- **UI Enhancements:**
  - Added CSS for the fixed `.cart-launcher` button.
  - Added hover-based dropdown behavior for desktop screens (min-width: 992px).

## Backend (Views & URLs)
### `views.py`
- Added `get_producers_api(request)` to provide a JSON list of producers (ID and Organization Name) for the search UI.
- Restored `add_to_cart(request, product_id)` that was inadvertently removed.

### `urls.py`
- Added `path('api/producers/', views.get_producers_api, name='api_producers')` to support the organization search dropdown.
