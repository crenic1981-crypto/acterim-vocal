"""Test Sub-agent Piete v3.2 — mode réactif par SIREN.
Rulare: python test_sub_agent_piete.py
"""
import asyncio, sys
sys.path.insert(0, ".")
from src.sub_agent_piete import check_company, scan_all_sources

async def test_reactiv():
    print("=== MODE RÉACTIF — vérification chantiers ELECTRICITE PETER ===")
    result = await check_company(siren="394905517", societe="ELECTRICITE ELECTRONIQUE PETER")
    print(f"Firma      : {result['societe']}")
    print(f"Santiere   : {result['nb_santiere_active']}")
    print(f"Luni max   : {result['luni_pe_santier_max']}")
    print(f"Surse OK   : {result['surse_consultate'] - result['surse_eshuate']}/{result['surse_consultate']}")
    if result["santiere_active"]:
        for s in result["santiere_active"]:
            print(f"  [{s['source']}] {s.get('titre','')[:70]}")
            print(f"    {s.get('montant',0)}EUR | {s.get('lieu','')} | {s.get('luni_pe_santier','')} luni")
    else:
        print("  Aucun chantier actif >= 3 luni detectat (firma ramane prospect activ)")
    print()

async def test_scan():
    print("=== MODE SCAN — 30 zile Grand Est BTP ===")
    result = await scan_all_sources(jours=30, force=True)
    print(f"Surse active : {result['surse_active']}/11")
    print(f"Marchés găsite: {result['total_marches']}")
    for m in result["marches"][:3]:
        print(f"  [{m['source']}] {m.get('attributaire','?')} — {m.get('titre','')[:60]}")
    print()

if __name__ == "__main__":
    asyncio.run(test_reactiv())
    asyncio.run(test_scan())
