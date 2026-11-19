"""Score the 50-post hand-check: writes hand_check.csv and prints the accuracy tables."""
import csv, json, math
from collections import defaultdict
from judgments import J

STRICT_FLIPS = {5, 9, 10, 12, 29, 31}  # rows whose verdict flips if "fresher" means a 0-year minimum

def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); r = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c - r)/d, (c + r)/d)

s = json.load(open("sample50.json"))
rows = []
for n, j in enumerate(s, 1):
    truth, cat, typ, mode, loc, exp, skills, evidence, note = J[n]
    shown = j["eligibility"] == "eligible"
    correct = shown == (truth == "FIT")
    strict_correct = (not correct) if n in STRICT_FLIPS else correct
    err = "" if correct else ("False positive (shown, should be hidden)" if shown else "Missed (hidden, should be shown)")
    rows.append({
        "#": n, "job_id": j["id"], "stratum": j["stratum"], "company": j["company"], "title": j["title"],
        "posting_url": j["apply_url"],
        "pipeline_label": j["eligibility"], "decided_by": j["classified_by"], "pipeline_reason": j["eligibility_reason"],
        "ai_fresher_friendly": (j["enrichment"] or {}).get("fresher_friendly", ""),
        "ai_confidence": (j["enrichment"] or {}).get("confidence", ""),
        "shown_on_site": "yes" if shown else "no",
        "hand_check_truth": truth, "decision_correct": "Y" if correct else "N", "error_type": err,
        "strict_reading_correct": "Y" if strict_correct else "N",
        "category": j["category"], "category_ok": cat, "employment_type": j["employment_type"], "employment_type_ok": typ,
        "work_mode": j["work_mode"], "work_mode_ok": mode, "cities": ", ".join(j["cities"]), "location_ok": loc,
        "experience": f"{j['experience_min']}-{j['experience_max']}", "experience_ok": exp,
        "skills": ", ".join(j["skills"]), "skills_ok": skills,
        "evidence_from_posting": evidence, "note": note, "your_check (Y/N)": "",
        "_pop": j["stratum_population"],
    })

with open("hand_check.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[k for k in rows[0] if not k.startswith("_")])
    w.writeheader(); [w.writerow({k: v for k, v in r.items() if not k.startswith("_")}) for r in rows]

out = {}
k = sum(r["decision_correct"] == "Y" for r in rows); out["raw"] = (k, len(rows), wilson(k, len(rows)))
ks = sum(r["strict_reading_correct"] == "Y" for r in rows); out["strict"] = (ks, len(rows))
by = defaultdict(list)
for r in rows: by[r["stratum"]].append(r)
strata = []
tot_pop = sum(v[0]["_pop"] for v in by.values()); weighted = 0
for name, rs in by.items():
    c = sum(r["decision_correct"] == "Y" for r in rs); pop = rs[0]["_pop"]
    weighted += pop * c / len(rs); strata.append((name, pop, len(rs), c, wilson(c, len(rs))))
out["weighted"] = weighted / tot_pop; out["pop"] = tot_pop
shown = [r for r in rows if r["shown_on_site"] == "yes"]
pub_pop = {r["stratum"]: r["_pop"] for r in shown}
pub_prec = sum(pub_pop[st] * sum(r["decision_correct"]=="Y" for r in shown if r["stratum"]==st) /
               sum(1 for r in shown if r["stratum"]==st) for st in pub_pop) / sum(pub_pop.values())
ai_final = [r for r in rows if r["decided_by"] == "ai"]
fields = {}
for f in ["category_ok", "employment_type_ok", "work_mode_ok", "location_ok", "experience_ok", "skills_ok"]:
    vals = [r[f] for r in rows if r[f] != "-"]
    fields[f] = (sum(v == "Y" for v in vals), sum(v == "N" for v in vals), sum(v == "U" for v in vals), len(vals))

print(f"Decision (shown/hidden) accuracy, raw: {k}/50 = {k/50:.0%}  95% CI {out['raw'][2][0]:.0%}-{out['raw'][2][1]:.0%}")
print(f"Strict reading (fresher = no experience required): {ks}/50 = {ks/50:.0%}")
print(f"Population-weighted accuracy over {tot_pop} processed India postings: {out['weighted']:.1%}")
print(f"Published list precision (weighted): {pub_prec:.1%}  (sample: {sum(r['decision_correct']=='Y' for r in shown)}/{len(shown)})")
print(f"AI made the final call: {sum(r['decision_correct']=='Y' for r in ai_final)}/{len(ai_final)}")
print("Errors:"); [print("  #", r["#"], r["company"], "|", r["title"], "->", r["error_type"]) for r in rows if r["error_type"]]
print("\nStratum | population | sampled | correct | 95% CI")
for name, pop, n, c, ci in strata: print(f"{name} | {pop} | {n} | {c}/{n} ({c/n:.0%}) | {ci[0]:.0%}-{ci[1]:.0%}")
print("\nField | correct | wrong | unknown | checked")
for f, (y, no, u, n) in fields.items(): print(f"{f} | {y} ({y/n:.0%}) | {no} | {u} | {n}")
json.dump({"strata": strata, "fields": fields, **out, "published_precision": pub_prec}, open("scores.json", "w"), indent=1, default=str)
