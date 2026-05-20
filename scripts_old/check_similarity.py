"""Check similarity between Vengeance and Vigilance."""
from difflib import SequenceMatcher

s1 = "vengeance"
s2 = "vigilance"

ratio = SequenceMatcher(None, s1, s2).ratio()
print(f"Similarity between '{s1}' and '{s2}': {ratio:.2f}")
print(f"Current threshold: 0.45")
print(f"Would match: {'YES ❌' if ratio >= 0.45 else 'NO ✅'}")
print()
print(f"Recommended threshold: 0.75")
print(f"Would match with 0.75: {'YES ❌' if ratio >= 0.75 else 'NO ✅'}")
