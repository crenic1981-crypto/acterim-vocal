# Codes effectif INSEE (`tranche_effectif_salarie`)

| Code | Tranche |
|---|---|
| NN | Unités non employeuses / Non renseigné |
| 00 | 0 salarié |
| 01 | 1 ou 2 salariés |
| 02 | 3 à 5 salariés |
| 03 | 6 à 9 salariés |
| 11 | **10 à 19 salariés** ✅ cible |
| 12 | **20 à 49 salariés** ✅ cible |
| 21 | 50 à 99 salariés |
| 22 | 100 à 199 salariés |
| 31 | 200 à 249 salariés |
| 32 | 250 à 499 salariés |
| 41 | 500 à 999 salariés |
| 42 | 1 000 à 1 999 salariés |
| 51 | 2 000 à 4 999 salariés |
| 52 | 5 000 à 9 999 salariés |
| 53 | 10 000 salariés et plus |

## Cible ACTERIM

```python
EFFECTIF_ACCEPTE = {"11", "12"}  # 10-49
```

`NN` (inconnu) est accepté (laisse passer en absence d'info — un humain qualifiera en aval).
Tout le reste est rejeté.

## Pour élargir/restreindre

- Ajouter les TPE (3-9 salariés) : inclure `"02"` et `"03"`.
- Monter aux ETI (50-99) : ajouter `"21"`.
- Strict ≥ 20 : restreindre à `{"12"}`.

Modifier `EFFECTIF_ACCEPTE` dans `bot_telegram.py` ET `reprocess_excel.py` simultanément.
