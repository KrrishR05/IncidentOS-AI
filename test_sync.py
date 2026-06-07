import sys; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv()
import memory

print("syntax OK")
items = memory._fetch_list_memories()
print(f"list_memories fetched: {len(items)} raw items")

parsed = [memory._parse_cloud_item(i) for i in items]
good = [p for p in parsed if p]
print(f"parsed with incident_id: {len(good)}")

resolved = [p for p in good if p.get("root_cause")]
print(f"of those, resolved: {len(resolved)}")

if good:
    print("\nSample parsed items:")
    for p in good[:5]:
        print(f"  {p['incident_id']}: {p['title'][:50]}  rc={repr(p.get('root_cause',''))[:40]}")
