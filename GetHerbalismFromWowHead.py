import re
import requests
import json
import csv

def extract_mapper_data(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    html = response.text
    
    pattern = r'var\s+g_mapperData\s*=\s*({.*?});'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        print(f"❌ g_mapperData introuvable pour {url}")
        return None
    
    json_str = re.sub(r'(\d+)(?=\s*:)', r'"\1"', match.group(1))
    json_str = re.sub(r'\\u00e9', 'é', json_str)
    json_str = re.sub(r'\\u00e2', 'â', json_str)
    
    try:
        return json.loads(json_str)
    except:
        return None

def add_coords_to_zone(zone_data, coords, plant_id):
    """Ajoute des coordonnées à une zone existante"""
    for coord in coords:
        if isinstance(coord, list) and len(coord) == 2:
            x, y = coord
            key = f"{int(x*100):04d}{int(y*100):04d}00"
            zone_data.setdefault(key, plant_id)

# 1. Lire le CSV des plantes
csv_data = """url;nom;code
https://www.wowhead.com/fr/object=516936/feuille-d-argent;feuille d'argent;1481
https://www.wowhead.com/fr/object=516935/azeracine;azeracine;1482
https://www.wowhead.com/fr/object=516937/lys-de-mana;lys de mana;1483
https://www.wowhead.com/fr/object=516934/sanguironce;sanguironce;1484
https://www.wowhead.com/fr/object=516932/tranquillette;tranquillette;1485"""

plants = []
reader = csv.DictReader(csv_data.splitlines(), delimiter=';')
for row in reader:
    plants.append({
        'url': row['url'],
        'name': row['nom'].strip(),
        'id': int(row['code'])
    })

# 2. FUSIONNER TOUTES LES COORDONNÉES par zone
zone_database = {}  # { zone_id: { coord_key: plant_id } }

print("📥 Récupération des données...")
for plant in plants:
    print(f"  {plant['name']} (ID: {plant['id']})...")
    data = extract_mapper_data(plant['url'])
    
    if data:
        for zone_key, zone_data in data.items():
            if isinstance(zone_data, list):
                zone_entry = zone_data[0]
                coords = zone_entry.get("coords", [])
                zone_id = zone_entry.get("uiMapId", int(zone_key))
                
                # Ajouter à la base fusionnée
                if zone_id not in zone_database:
                    zone_database[zone_id] = {}
                add_coords_to_zone(zone_database[zone_id], coords, plant['id'])
        
        print(f"    ✅ Ajouté")
    else:
        print(f"    ❌ Erreur")

# 3. Générer Lua FUSIONNÉ (format exact de ton fichier)
lines = ["-- GatherMate2 Multi-Plantes FUSIONNÉ (GatherMateData2HerbDB)"]
lines.append("GatherMateData2HerbDB = GatherMateData2HerbDB or {}")

for zone_id in sorted(zone_database.keys()):
    lines.append(f"\t[{zone_id}] = {{")
    
    # Trier les coordonnées par clé pour lisibilité
    sorted_coords = sorted(zone_database[zone_id].items())
    for coord_key, plant_id in sorted_coords:
        lines.append(f"\t\t[{coord_key}] = {plant_id},")
    
    lines.append("\t},")

# Écriture
with open("GatherMateData2_herbalism_midnight.lua", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n🎉 Fichier créé : GatherMateData2_herbalism_midnight.lua")
print(f"📊 {len(zone_database)} zones uniques traitées")
print("📋 Copie dans HerbalismData.lua → /reload")

