                # 3 skambučiai / ratą — KIEKVIENAS kitas seed (nesikartoja), mokykla renkasi geriausias
                phone_lines = list(VILKAS8_PHONE)
                for n, need in ((1, 14), (2, 34), (3, 46)):
                    need_use = (12 + (n - 1) * 18) if use_elapsed else need
                    gate = elapsed if use_elapsed else quiet
                    if gate >= need_use and remain > 8:
                        # seed keičiasi kas ~2 min + pagal n → frazės sukasi, neįkyri tos pačios
                        phone_seed = int(lot["id"]) * 31 + n * 97 + int(now // 120)
                        # Ankstesnis įvykis buvo "phone" (Vilkas ką tik kalbėjo telefonu) →
                        # tęsiam su phone_catchup frazėmis ir pažymim {"catchup": True}.
                        _ph_round = f"{lot['id']}:{_sa}"
                        _ph_catchup = (_VP_PHONE_ROUND.get("key") == _ph_round)
                        _ph_part = _vp("phone_catchup" if _ph_catchup else "phone", phone_seed, phone_lines)
                        _ph_payload = {"lot_id": lot["id"], "n": n, **_ph_part}
                        if _ph_catchup:
                            _ph_payload["catchup"] = True
                            try:
                                _ph_rows = con.execute(
                                    "SELECT name FROM bids WHERE lot_id=? ORDER BY id DESC LIMIT 8",
                                    (lot["id"],),
                                ).fetchall()
                                _ph_names = _vp_names_lt([r["name"] for r in _ph_rows])
                            except Exception:
                                _ph_names = ""
                            _ph_payload["text"] = str(_ph_payload.get("text") or "").replace(
                                "{vardai}", _ph_names or "dalyviai"
                            )
                        emit_event(
                            "phone",
                            _ph_payload,
                            35, 30,
                            f"phone:{lot['id']}:{_sa}" + ("" if n == 1 else f":{n}"),
                            con=con,
                        )
                        _VP_PHONE_ROUND["key"] = _ph_round
