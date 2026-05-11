import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# ── CATEGORIES & PRODUCTS ──
products = [
    # Fruit
    {"product_id": 1,  "product_name": "Organic Apples",       "category": "Fruit",  "price": 3.50, "seasonal_months": None},
    {"product_id": 2,  "product_name": "Bananas",               "category": "Fruit",  "price": 1.80, "seasonal_months": None},
    {"product_id": 3,  "product_name": "Strawberries",          "category": "Fruit",  "price": 4.20, "seasonal_months": [5,6,7,8]},
    {"product_id": 4,  "product_name": "Blueberries",           "category": "Fruit",  "price": 3.80, "seasonal_months": [6,7,8]},
    {"product_id": 5,  "product_name": "Oranges",               "category": "Fruit",  "price": 2.50, "seasonal_months": [11,12,1,2]},
    {"product_id": 6,  "product_name": "Grapes",                "category": "Fruit",  "price": 3.20, "seasonal_months": [8,9,10]},
    {"product_id": 7,  "product_name": "Pears",                 "category": "Fruit",  "price": 2.80, "seasonal_months": [9,10,11]},
    {"product_id": 8,  "product_name": "Cherries",              "category": "Fruit",  "price": 5.50, "seasonal_months": [6,7]},
    {"product_id": 9,  "product_name": "Peaches",               "category": "Fruit",  "price": 4.00, "seasonal_months": [7,8,9]},
    {"product_id": 10, "product_name": "Raspberries",           "category": "Fruit",  "price": 4.50, "seasonal_months": [6,7,8]},
    # Veg
    {"product_id": 11, "product_name": "Carrots",               "category": "Veg",    "price": 1.20, "seasonal_months": None},
    {"product_id": 12, "product_name": "Broccoli",              "category": "Veg",    "price": 1.80, "seasonal_months": None},
    {"product_id": 13, "product_name": "Spinach",               "category": "Veg",    "price": 2.00, "seasonal_months": None},
    {"product_id": 14, "product_name": "Courgettes",            "category": "Veg",    "price": 1.50, "seasonal_months": [6,7,8,9]},
    {"product_id": 15, "product_name": "Pumpkin",               "category": "Veg",    "price": 3.50, "seasonal_months": [9,10,11]},
    {"product_id": 16, "product_name": "Asparagus",             "category": "Veg",    "price": 4.00, "seasonal_months": [4,5,6]},
    {"product_id": 17, "product_name": "Leeks",                 "category": "Veg",    "price": 1.60, "seasonal_months": [10,11,12,1,2]},
    {"product_id": 18, "product_name": "Tomatoes",              "category": "Veg",    "price": 2.20, "seasonal_months": [6,7,8,9]},
    {"product_id": 19, "product_name": "Cucumber",              "category": "Veg",    "price": 1.30, "seasonal_months": None},
    {"product_id": 20, "product_name": "Peppers",               "category": "Veg",    "price": 2.00, "seasonal_months": None},
    # Dairy
    {"product_id": 21, "product_name": "Free Range Eggs",       "category": "Dairy",  "price": 4.20, "seasonal_months": None},
    {"product_id": 22, "product_name": "Whole Milk (2L)",       "category": "Dairy",  "price": 2.10, "seasonal_months": None},
    {"product_id": 23, "product_name": "Cheddar Cheese",        "category": "Dairy",  "price": 5.50, "seasonal_months": None},
    {"product_id": 24, "product_name": "Greek Yoghurt",         "category": "Dairy",  "price": 3.00, "seasonal_months": None},
    {"product_id": 25, "product_name": "Butter",                "category": "Dairy",  "price": 3.20, "seasonal_months": None},
    {"product_id": 26, "product_name": "Cream",                 "category": "Dairy",  "price": 2.50, "seasonal_months": None},
    {"product_id": 27, "product_name": "Brie",                  "category": "Dairy",  "price": 6.00, "seasonal_months": None},
    {"product_id": 28, "product_name": "Feta Cheese",           "category": "Dairy",  "price": 4.50, "seasonal_months": None},
    {"product_id": 29, "product_name": "Skimmed Milk (2L)",     "category": "Dairy",  "price": 1.90, "seasonal_months": None},
    {"product_id": 30, "product_name": "Crème Fraîche",         "category": "Dairy",  "price": 2.80, "seasonal_months": None},
    # Bakery
    {"product_id": 31, "product_name": "Sourdough Bread",       "category": "Bakery", "price": 5.00, "seasonal_months": None},
    {"product_id": 32, "product_name": "Wholemeal Loaf",        "category": "Bakery", "price": 3.50, "seasonal_months": None},
    {"product_id": 33, "product_name": "Croissants (4pk)",      "category": "Bakery", "price": 4.20, "seasonal_months": None},
    {"product_id": 34, "product_name": "Seeded Rolls (6pk)",    "category": "Bakery", "price": 3.00, "seasonal_months": None},
    {"product_id": 35, "product_name": "Cinnamon Swirls (4pk)", "category": "Bakery", "price": 4.50, "seasonal_months": None},
    {"product_id": 36, "product_name": "Focaccia",              "category": "Bakery", "price": 4.80, "seasonal_months": None},
    {"product_id": 37, "product_name": "Rye Bread",             "category": "Bakery", "price": 4.20, "seasonal_months": None},
    {"product_id": 38, "product_name": "Baguette",              "category": "Bakery", "price": 2.50, "seasonal_months": None},
    {"product_id": 39, "product_name": "Muffins (4pk)",         "category": "Bakery", "price": 3.80, "seasonal_months": None},
    {"product_id": 40, "product_name": "Bagels (5pk)",          "category": "Bakery", "price": 3.50, "seasonal_months": None},
    # Meat
    {"product_id": 41, "product_name": "Chicken Breast (500g)", "category": "Meat",   "price": 6.50, "seasonal_months": None},
    {"product_id": 42, "product_name": "Beef Mince (500g)",     "category": "Meat",   "price": 7.00, "seasonal_months": None},
    {"product_id": 43, "product_name": "Pork Sausages (6pk)",   "category": "Meat",   "price": 5.50, "seasonal_months": None},
    {"product_id": 44, "product_name": "Lamb Chops (400g)",     "category": "Meat",   "price": 9.00, "seasonal_months": None},
    {"product_id": 45, "product_name": "Smoked Bacon (300g)",   "category": "Meat",   "price": 5.00, "seasonal_months": None},
    {"product_id": 46, "product_name": "Turkey Breast (500g)",  "category": "Meat",   "price": 7.50, "seasonal_months": None},
    {"product_id": 47, "product_name": "Pork Belly (500g)",     "category": "Meat",   "price": 6.00, "seasonal_months": None},
    {"product_id": 48, "product_name": "Sirloin Steak (250g)",  "category": "Meat",   "price": 12.00,"seasonal_months": None},
    {"product_id": 49, "product_name": "Chicken Thighs (6pk)",  "category": "Meat",   "price": 5.80, "seasonal_months": None},
    {"product_id": 50, "product_name": "Venison Mince (400g)",  "category": "Meat",   "price": 9.50, "seasonal_months": None},
    # Pantry
    {"product_id": 51, "product_name": "Local Honey (340g)",    "category": "Pantry", "price": 6.50, "seasonal_months": None},
    {"product_id": 52, "product_name": "Rapeseed Oil (500ml)",  "category": "Pantry", "price": 5.00, "seasonal_months": None},
    {"product_id": 53, "product_name": "Oats (1kg)",            "category": "Pantry", "price": 3.00, "seasonal_months": None},
    {"product_id": 54, "product_name": "Wholegrain Pasta (500g)","category":"Pantry", "price": 2.80, "seasonal_months": None},
    {"product_id": 55, "product_name": "Lentils (500g)",        "category": "Pantry", "price": 2.50, "seasonal_months": None},
    {"product_id": 56, "product_name": "Chickpeas (400g tin)",  "category": "Pantry", "price": 1.80, "seasonal_months": None},
    {"product_id": 57, "product_name": "Basmati Rice (1kg)",    "category": "Pantry", "price": 3.50, "seasonal_months": None},
    {"product_id": 58, "product_name": "Apple Cider Vinegar",   "category": "Pantry", "price": 4.20, "seasonal_months": None},
    {"product_id": 59, "product_name": "Mixed Nuts (200g)",     "category": "Pantry", "price": 5.50, "seasonal_months": None},
    {"product_id": 60, "product_name": "Dried Cranberries (150g)","category":"Pantry","price": 3.80, "seasonal_months": None},
]

product_lookup = {p["product_id"]: p for p in products}

# ── PRODUCERS (map categories to producer IDs, starting at 7 to avoid fixture clash) ──
producer_map = {
    "Fruit":  7,
    "Veg":    8,
    "Dairy":  9,
    "Bakery": 10,
    "Meat":   11,
    "Pantry": 12,
}

# ── BUILD CUSTOMERS ──
NUM_CUSTOMERS = 250
customers = []

for i in range(NUM_CUSTOMERS):
    customer_id = i + 7  # avoid clash with fixtures
    # Pick 3–6 favourite products that this customer buys regularly
    num_faves = random.randint(3, 6)
    favourite_products = random.sample([p["product_id"] for p in products], num_faves)
    # Ordering frequency: roughly every N days
    frequency = random.randint(5, 14)  # 5=twice a week, 14=weekly-ish
    customers.append({
        "customer_id": customer_id,
        "favourite_products": favourite_products,
        "frequency": frequency,
    })

# ── GENERATE ORDERS ──
START_DATE = datetime(2025, 9, 1)
END_DATE   = datetime(2026, 8, 31)

rows = []
order_id = 1

for customer in customers:
    current_date = START_DATE + timedelta(days=random.randint(0, 14))  # stagger start

    while current_date <= END_DATE:
        # Decide how many items in this order (1–5)
        num_items = random.randint(1, 5)

        # Build item pool: favourites weighted heavily, occasional discovery item
        item_pool = customer["favourite_products"].copy()
        if random.random() < 0.3:  # 30% chance of a discovery item
            discovery = random.choice([p["product_id"] for p in products
                                       if p["product_id"] not in item_pool])
            item_pool.append(discovery)

        # Filter by seasonal availability
        month = current_date.month
        available = []
        for pid in item_pool:
            p = product_lookup[pid]
            seasonal = p["seasonal_months"]
            if seasonal is None or month in seasonal:
                available.append(pid)

        if not available:
            available = [random.choice(customer["favourite_products"])]

        chosen = random.sample(available, min(num_items, len(available)))

        order_total = 0
        order_date = current_date.strftime("%Y-%m-%d")
        delivery_date = (current_date + timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d")

        for pid in chosen:
            p = product_lookup[pid]
            quantity = random.randint(1, 4)
            line_total = round(p["price"] * quantity, 2)
            order_total += line_total

            rows.append({
                "order_id":    order_id,
                "customer_id": customer["customer_id"],
                "product_id":  pid,
                "product_name": p["product_name"],
                "category":    p["category"],
                "producer_id": producer_map[p["category"]],
                "quantity":    quantity,
                "price":       p["price"],
                "order_date":  order_date,
                "delivery_date": delivery_date,
                "order_total": round(order_total, 2),
                "status":      "delivered",
            })

        order_id += 1
        gap = customer["frequency"] + random.randint(-3, 3)
        current_date += timedelta(days=max(4, gap))

# ── SAVE CSV ──
output_file = "/mnt/user-data/outputs/purchase_history.csv"
fieldnames = ["order_id", "customer_id", "product_id", "product_name", "category",
              "producer_id", "quantity", "price", "order_date", "delivery_date",
              "order_total", "status"]

with open(output_file, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# ── SUMMARY ──
unique_orders    = len(set(r["order_id"] for r in rows))
unique_customers = len(set(r["customer_id"] for r in rows))
unique_products  = len(set(r["product_id"] for r in rows))

print(f"Generated {output_file}")
print(f"  {len(rows):,} order item rows")
print(f"  {unique_orders:,} orders")
print(f"  {unique_customers} customers")
print(f"  {unique_products} products")
print(f"  Date range: {rows[0]['order_date']} to {rows[-1]['order_date']}")
