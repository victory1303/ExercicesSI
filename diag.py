# diagnose_fix_attrs.py
import re
from pathlib import Path
import sys
p = Path("graphe.py")
if not p.exists():
    print("Fichier 'graphe.py' introuvable dans le répertoire courant.")
    sys.exit(1)

text = p.read_text(encoding="utf-8")

# trouver ranges des triple-quoted pour ignorer le HTML/JS
triple_pattern = re.compile(r'(""".*?"""|\'\'\'.*?\'\'\')', re.DOTALL)
triple_ranges = [(m.start(), m.end()) for m in triple_pattern.finditer(text)]

def in_triple(idx):
    for a,b in triple_ranges:
        if a <= idx < b:
            return True
    return False

# attributs d'intérêt (ceux qui sont dans les dict routes)
attrs = ["stops_count", "distance_m", "duration_s", "poly", "waypoints"]
attr_pattern = re.compile(r'\b([A-Za-z_]\w*)\.(' + '|'.join(attrs) + r')\b')

matches = []
for m in attr_pattern.finditer(text):
    if not in_triple(m.start()):
        line_no = text.count("\n", 0, m.start()) + 1
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1: line_end = len(text)
        line = text[line_start:line_end]
        matches.append((m.group(1), m.group(2), line_no, line.strip(), m.start(), m.end()))

if not matches:
    print("Aucune occurrence d'accès par attribut (e.g. obj.stops_count) trouvée hors blocs triple-quoted.")
    sys.exit(0)

print("Occurrences trouvées (hors triple-quoted) :")
for var, attr, ln, line, s,e in matches:
    print(f"  Ligne {ln}: variable '{var}' . '{attr}'  -->  {line}")

# question remplacement
ans = input("\nRemplacer automatiquement ces occurrences par obj[\"attr\"] ? (o/N) : ").strip().lower()
if ans != 'o':
    print("Aucun changement effectué. Corrige manuellement les lignes indiquées.")
    sys.exit(0)

# effectuer remplacements en construisant nouveau texte
new_text = []
last = 0
for var, attr, ln, line, s,e in matches:
    new_text.append(text[last:s])
    new_text.append(f'{var}["{attr}"]')
    last = e
new_text.append(text[last:])
backup = p.with_suffix(".py.bak")
backup.write_text(text, encoding="utf-8")
p.write_text(''.join(new_text), encoding="utf-8")
print(f"Remplacements effectués. Backup créé : {backup.name}")
print("Relance ton script : python graphe.py")
