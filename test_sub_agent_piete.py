"""Test rapid Sub-agent Piete — rulare: python test_sub_agent_piete.py"""
import asyncio, sys
sys.path.insert(0, ".")
from src.sub_agent_piete import scan_all_sources

async def test():
    print("Scan marchés Grand Est BTP — 30 zile...")
    results = await scan_all_sources(jours=30, force=True)
    print(f"Surse active : {results['surse_active']}/11")
    print(f"Surse eșuate: {results['surse_eshuate']}/11")
    print(f"Marchés găsite: {results['total_marches']}")
    print()
    for m in results["marches"][:5]:
        print(f"  [{m['source']}] {m.get('attributaire','?')} ({m.get('siren','?')})")
        print(f"    {m.get('titre','')[:80]}")
        print(f"    {m.get('montant',0)}€ · {m.get('lieu','')} · {m.get('date_attrib','')}")
        print()

if __name__ == "__main__":
    asyncio.run(test())
