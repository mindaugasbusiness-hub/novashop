# -*- coding: utf-8 -*-
"""FAQ atpazinimo testas (offline, be HTTP)."""
import sys

sys.path.insert(0, "/opt/aukcionas")
import ivr  # noqa: E402

CASES = [
    ("noriu perduoti preke aukcionui", 1),
    ("kur galiu atvezti preke", 2),
    ("kada prasideda aukcionas", 3),
    ("kaip uzsiregistruoti", 4),
    ("kaip nupirkti daikta", 5),
    ("kaip moketi uz laimeta preke", 6),
    ("kada gausiu siunta", 7),
    ("ar yra garantija", 8),
    ("kiek imate komisiniu", 9),
    ("ar galiu atsiimti vietoje", 10),
    ("kiek trunka vienas lotas", 11),
    ("kaip suzinoti ar laimejau", 12),
    ("jusu telefono numeris", 13),
    ("kas tas vilkas", 14),
    ("ar galima apziureti preke pries perkant", 15),
    ("ar galima moketi kortele", 16),
    ("kiek prekiu buna per vakara", 17),
    ("ar siunciate i uzsieni", 18),
    ("mano preke neveikia", 19),
    ("kaip atsiimti laimeta preke", 20),
    ("kur atsiimti", 20),
    ("pristatymas i pastomata", 7),
    ("labas vakaras", None),
]

ok = bad = 0
for phrase, want in CASES:
    entry, score = ivr.faq_match(phrase)
    got = entry.get("nr") if entry else None
    good = got == want
    ok += 1 if good else 0
    bad += 0 if good else 1
    print(f"{'OK  ' if good else 'FAIL'} '{phrase}' -> nr={got} (tikejausi {want}) balas={round(score, 2)}"
          + (f" [{entry.get('tema')}]" if entry else ""))
print(f"\nFAQ testas: OK={ok} FAIL={bad} is {len(CASES)}")
