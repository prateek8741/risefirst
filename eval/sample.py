"""Draw the 50-post stratified hand-check sample from a frozen snapshot (seeded, reproducible)."""
import json, random, re, sys

SNAPSHOT = "snapshot_2026-11-19.json"
STRATA = [  # (name, predicate, n)
    ("S1 published, rules decided", lambda j: j["eligibility"] == "eligible" and j["classified_by"] == "rules", 12),
    ("S2 published, AI decided",    lambda j: j["eligibility"] == "eligible" and j["classified_by"] == "ai", 8),
    ("S3 rejected by AI",           lambda j: j["eligibility"] == "rejected" and j["classified_by"] == "ai", 8),
    ("S4 review, AI read it",       lambda j: j["eligibility"] == "review_required" and j["enrichment"], 7),
    ("S5 rejected by rules",        lambda j: j["eligibility"] == "rejected" and j["classified_by"] == "rules", 15),
]

jobs = json.load(open(SNAPSHOT))
rng = random.Random(20261119)
sample = []
for name, pred, n in STRATA:
    pool = [j for j in jobs if pred(j)]
    picked = rng.sample(pool, min(n, len(pool)))
    for j in sorted(picked, key=lambda j: j["id"]):
        sample.append({"stratum": name, "stratum_population": len(pool), **j})
json.dump(sample, open("sample50.json", "w"), indent=1)
print(len(sample), "sampled")
