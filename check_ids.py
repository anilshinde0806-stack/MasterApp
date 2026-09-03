import re

with open('core/templates/jobcard/jobcardEntry.html', 'r', encoding='utf-8') as f:
    content = f.read()
    ids = re.findall(r'id=["\'](.*?)["\']', content)
    
    seen = set()
    dupes = []
    for id_val in ids:
        if id_val in seen:
            dupes.append(id_val)
        seen.add(id_val)
    
    if dupes:
        print("Duplicate IDs found:")
        for dupe in set(dupes):
            print(f"- {dupe}")
    else:
        print("No duplicate IDs found.")
