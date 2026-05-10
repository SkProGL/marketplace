import csv
import os

def assign_allergens(name, category, description):
    allergens = []
    name_lower = name.lower()
    desc_lower = description.lower()
    
    # Dairy
    if 'milk' in name_lower or 'yogurt' in name_lower or 'butter' in name_lower or 'cheese' in name_lower or 'brie' in name_lower or 'mozzarella' in name_lower or 'cream' in name_lower or 'parmesan' in name_lower or 'cheddar' in name_lower:
        allergens.append('Milk')
    
    # Eggs
    if 'egg' in name_lower or 'muffin' in name_lower or 'scone' in name_lower or 'croissant' in name_lower or 'brioche' in name_lower:
        allergens.append('Eggs')
        
    # Gluten
    if category == 'bakery' or 'bread' in name_lower or 'baguette' in name_lower or 'muffin' in name_lower or 'scone' in name_lower or 'bun' in name_lower or 'bagel' in name_lower or 'ciabatta' in name_lower or 'sourdough' in name_lower:
        allergens.append('Gluten')
        
    # Peanuts
    if 'peanut' in name_lower:
        allergens.append('Peanuts')
        
    # Nuts (General/Tree nuts)
    if 'pesto' in name_lower or 'pine nut' in desc_lower:
        allergens.append('Nuts')
        
    # Sesame
    if 'sesame' in name_lower:
        allergens.append('Sesame')
        
    return ', '.join(set(allergens))

input_file = '/mnt/c/Users/glebi/Desktop/desd/tutorial_repo/marketplace_platform/synthetic_data/products.csv'
output_file = '/mnt/c/Users/glebi/Desktop/desd/tutorial_repo/marketplace_platform/synthetic_data/a_products.csv'

with open(input_file, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    
    rows = []
    for row in reader:
        row['allergens'] = assign_allergens(row['name'], row['category'], row['description'])
        rows.append(row)

with open(output_file, mode='w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Successfully processed {len(rows)} products. Output saved to {output_file}")
