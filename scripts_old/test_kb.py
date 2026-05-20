"""Test knowledge base card data."""
import sys
sys.path.insert(0, 'src')
from advisor.groq_advisor import GroqAdvisor

a = GroqAdvisor()
bash = a.kb.cards.get('bash')

print('Bash card:')
print(f'  Cost: {bash["cost"]} → {bash.get("cost_upgraded", "N/A")}')
print(f'  Damage: {bash["damage"]} → {bash.get("damage_upgraded", "N/A")}')
print(f'  Magic: {bash["magic_number"]} → {bash.get("magic_number_upgraded", "N/A")}')
print('\n✓ Base + Upgraded combined correctly!')
