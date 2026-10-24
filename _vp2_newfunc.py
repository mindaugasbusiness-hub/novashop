def _vp(kind, seed, fallback_list):
    """Frazes parinkimas: 0.45*kokybe + 0.40*atsitiktinumas + 0.15*naujumas.
    Kartu balansavimas: jei fraze panaudota daugiau nei 2x nei vidurkis, kokybes svoris *0.5.
    Kokybe ir naujumas normalizuojami (pool) ir suspaudziami (BALANS), kad istoriniai
    a/b bei kartai neuzgoztu atsitiktinumo — taip apseina VISOS aktyvios frazes.
    To paties kind frazes nesikartoja: paskutines 8 laikomos atmintyje,
    dvieju is eiles vienodu nebus. Grazina payload dali {"text","phrase_id"}."""
    try:
        arr = [p for p in (vilko_brain().get("frazes") or {}).get(kind, []) if p.get("aktyvi", True) and p.get("tekstas")]
    except Exception:
        arr = []
    if not arr:
        fl = list(fallback_list or [""])
        return {"text": fl[int(seed) % len(fl)], "phrase_id": None}
    recent = _VP_RECENT.setdefault(kind, deque(maxlen=8))
    pool = [p for p in arr if str(p.get("id")) not in recent]
    if not pool:
        pool = list(arr)
    last = _VP_LAST.get(kind)
    if len(pool) > 1 and last is not None:
        pool = [p for p in pool if str(p.get("id")) != str(last)] or pool

    def _num(p, key, dflt):
        try:
            return float(p.get(key) or dflt)
        except Exception:
            return float(dflt)

    mean_kartai = (sum(_num(p, "kartai", 0.0) for p in arr) / len(arr)) if arr else 0.0
    rows = []
    for p in pool:
        a = max(0.01, _num(p, "a", 1.0))
        b = max(0.01, _num(p, "b", 1.0))
        kartai = max(0.0, _num(p, "kartai", 0.0))
        kokybe = a / (a + b)
        if mean_kartai > 0 and kartai > 2.0 * mean_kartai:
            kokybe *= 0.5  # kartu balansavimas: permegstama fraze pristabdoma
        naujumas = 1.0 / (1.0 + kartai / 10.0)
        rows.append((p, kokybe, naujumas))
    qmin = min(r[1] for r in rows)
    qmax = max(r[1] for r in rows)
    nmin = min(r[2] for r in rows)
    nmax = max(r[2] for r in rows)
    BALANS = 0.03  # balansuotas svertas: kokybe/naujumas — tik tiebreaker'iai
    rnd = _vk_random.Random(f"{kind}:{seed}:{time.time_ns()}")
    best, bv = None, -1.0
    for p, kokybe, naujumas in rows:
        qrel = (kokybe - qmin) / (qmax - qmin) if qmax > qmin else 0.5
        nrel = (naujumas - nmin) / (nmax - nmin) if nmax > nmin else 0.5
        score = (0.45 * (0.5 + BALANS * (qrel - 0.5))
                 + 0.40 * rnd.random()
                 + 0.15 * (0.5 + BALANS * (nrel - 0.5)))
        if score > bv:
            best, bv = p, score
    chosen = str(best.get("id"))
    recent.append(chosen)
    _VP_LAST[kind] = chosen
    return {"text": best["tekstas"], "phrase_id": best.get("id")}


def _vp_names_lt(names):
    """Vardu sarasas lietuviskai: X | X ir Y | X, Y ir Z (phone_catchup {vardai})."""
    uniq = []
    for nm in names or []:
        parts = str(nm or "").strip().split()
        nm1 = parts[0] if parts else ""
        if not nm1:
            continue
        if nm1.lower() in [u.lower() for u in uniq]:
            continue
        uniq.append(nm1)
    if not uniq:
        return ""
    if len(uniq) == 1:
        return uniq[0]
    if len(uniq) == 2:
        return uniq[0] + " ir " + uniq[1]
    return ", ".join(uniq[:-1]) + " ir " + uniq[-1]
