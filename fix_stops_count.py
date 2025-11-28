# fix_stops_count.py
import io
import re
import sys
from pathlib import Path

p = Path("graphe.py")
if not p.exists():
    print("Fichier 'graphe.py' introuvable dans le répertoire courant.")
    sys.exit(1)

text = p.read_text(encoding="utf-8")

# We will scan and find .stops_count occurrences outside triple-quoted strings
# Strategy: find ranges of triple-quoted strings and ignore matches inside them.

triple_quote_ranges = []
pattern_triple = re.compile(r'(""".*?"""|\'\'\'.*?\'\'\')', re.DOTALL)
for m in pattern_triple.finditer(text):
    triple_quote_ranges.append((m.start(), m.end()))

def in_triple(pos):
    for a,b in triple_quote_ranges:
        if a <= pos < b:
            return True
    return False

pattern = re.compile(r'\.stops_count\b')
matches = list(pattern.finditer(text))

if not matches:
    print("Aucune occurrence de `.stops_count` trouvée dans le code (hors blocs triple-quoted).")
    sys.exit(0)

print("Occurrences de `.stops_count` (hors triple-quoted) :")
occ_list = []
for m in matches:
    if not in_triple(m.start()):
        # get line number and line
        line_no = text.count("\n", 0, m.start()) + 1
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        print(f"  Ligne {line_no}: {line.strip()}")
        occ_list.append((m.start(), m.end(), line_no, line))

if not occ_list:
    print("Aucune occurrence hors triple-quoted après filtrage.")
    sys.exit(0)

# ASK user whether to replace automatically
resp = input("\nRemplacer automatiquement ces occurrences par [\"stops_count\"] ? (o/N) : ").strip().lower()
if resp != 'o':
    print("Aucun changement effectué. Corrige manuellement les lignes indiquées.")
    sys.exit(0)

# Perform replacements but only at the specific positions captured (we rebuild text)
new_text_parts = []
last_idx = 0
for start, end, _, _ in occ_list:
    new_text_parts.append(text[last_idx:start])
    new_text_parts.append('["stops_count"]')
    last_idx = end
new_text_parts.append(text[last_idx:])
new_text = "".join(new_text_parts)

backup = p.with_suffix(".py.bak")
p.write_text(backup.read_text(encoding="utf-8") if backup.exists() else text, encoding="utf-8")  # ensure backup exists
p.write_text(new_text, encoding="utf-8")
print(f"Remplacement effectué. Sauvegarde originale : {backup.name}")
print("Tu peux réexécuter : python graphe.py")
