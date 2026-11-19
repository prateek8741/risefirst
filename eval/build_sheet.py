"""Build RiseFirst_eval.xlsx (upload to Google Sheets) from the eval files in this folder."""
import csv, json
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

import sys
sys.path.insert(0, "../backend/src")

FONT = "Arial"
HEAD = PatternFill("solid", fgColor="1F3864")
INPUT = Font(name=FONT, color="0000FF")
BOLD = Font(name=FONT, bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")

rows = list(csv.DictReader(open("hand_check.csv")))
usage = json.load(open("token_usage.json"))
schema = json.load(open("gemini_output_schema.json"))
snapshot = json.load(open("snapshot_2026-11-19.json"))
runs = [
    # id, started (UTC), fetched, india, eligible, review, rejected, ai_calls, ai_failures, ai_cache_hits, ai_skipped, model, note
    (1, "2026-11-19 06:53", 11848, 1527, 40, 258, 1229, 0, 0, 0, 0, "none (rules only)", "Baseline, no API key"),
    (2, "2026-11-19 12:39", 11861, 1536, 43, 253, 1240, 297, 287, 0, 0, "gemini-3.5-flash",
     "Free tier: 5 req/min, 20 req/day. 4 threads hit 429s; 287 of 297 calls failed"),
    (3, "2026-11-19 12:47", 11861, 1536, 43, 253, 1240, 4, 4, 10, 283, "gemini-3.5-flash",
     "After fix: 10 cache hits, daily quota detected once, AI paused, 283 deferred to next run"),
    (4, "2026-11-19 12:55", None, None, None, None, None, None, None, None, None, "gemini-3.5-flash-lite",
     "Separate quota; paced at 5 req/min, 503s retried. Still running when the sample was frozen"),
]

from risefirst.infrastructure.llm.gemini import SYSTEM_INSTRUCTION, PROMPT_VERSION, _MAX_DESCRIPTION_CHARS  # noqa: E402

wb = Workbook()


def style_header(ws, row=1):
    for c in ws[row]:
        if c.value is not None:
            c.font = Font(name=FONT, bold=True, color="FFFFFF")
            c.fill = HEAD
            c.alignment = Alignment(wrap_text=True, vertical="center")


def set_font(ws):
    for row in ws.iter_rows():
        for c in row:
            if c.font is None or c.font.name != FONT:
                c.font = Font(name=FONT, bold=c.font.bold if c.font else False,
                              color=c.font.color if c.font else None)


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[get_column_letter(i)].width = x


# ---------------- Hand-check (50) ----------------
hc = wb.active
hc.title = "Hand-check (50)"
cols = list(rows[0].keys())
hc.append(cols)
for r in rows:
    vals = []
    for k in cols:
        v = r[k]
        if k in ("#", "job_id"):
            v = int(v)
        elif k == "ai_confidence" and v != "":
            v = float(v)
        vals.append(v)
    hc.append(vals)
style_header(hc)
hc.freeze_panes = "F2"
hc.auto_filter.ref = hc.dimensions
col = {k: get_column_letter(i + 1) for i, k in enumerate(cols)}
for row in hc.iter_rows(min_row=2):
    for c in row:
        c.font = Font(name=FONT)
        c.alignment = Alignment(vertical="top", wrap_text=cols[c.column - 1] in ("title", "evidence_from_posting", "note", "pipeline_reason", "skills"))
    for c in row:
        if cols[c.column - 1] == "your_check (Y/N)":
            c.fill = PatternFill("solid", fgColor="FFFF00")
        if cols[c.column - 1] == "decision_correct" and c.value == "N":
            c.fill = PatternFill("solid", fgColor="F4CCCC")
widths(hc, [4, 7, 24, 12, 34, 30, 14, 9, 28, 9, 9, 8, 10, 9, 26, 9, 18, 8, 13, 8, 9, 8, 18, 8, 10, 8, 30, 8, 48, 48, 12])
N = len(rows) + 1  # last data row

# ---------------- Strata ----------------
st = wb.create_sheet("Strata")
st.append(["Stratum", "Population (India postings)", "Sampled", "Decision correct", "Accuracy", "Weight x accuracy"])
strata = []
for r in rows:
    if r["stratum"] not in strata:
        strata.append(r["stratum"])
pop = {}
preds = {
    "S1 published, rules decided": lambda j: j["eligibility"] == "eligible" and j["classified_by"] == "rules",
    "S2 published, AI decided": lambda j: j["eligibility"] == "eligible" and j["classified_by"] == "ai",
    "S3 rejected by AI": lambda j: j["eligibility"] == "rejected" and j["classified_by"] == "ai",
    "S4 review, AI read it": lambda j: j["eligibility"] == "review_required" and j["enrichment"],
    "S5 rejected by rules": lambda j: j["eligibility"] == "rejected" and j["classified_by"] == "rules",
}
for i, s in enumerate(strata, 2):
    pop[s] = sum(1 for j in snapshot if preds[s](j))
    st.append([s, pop[s],
               f"=COUNTIF('Hand-check (50)'!${col['stratum']}$2:${col['stratum']}${N},A{i})",
               f"=COUNTIFS('Hand-check (50)'!${col['stratum']}$2:${col['stratum']}${N},A{i},'Hand-check (50)'!${col['decision_correct']}$2:${col['decision_correct']}${N},\"Y\")",
               f"=IF(C{i}=0,0,D{i}/C{i})", f"=B{i}*E{i}"])
    st.cell(i, 2).font = INPUT
last = len(strata) + 1
st.append(["Total", f"=SUM(B2:B{last})", f"=SUM(C2:C{last})", f"=SUM(D2:D{last})", f"=D{last+1}/C{last+1}", f"=SUM(F2:F{last})"])
st.append(["Population-weighted accuracy", None, None, None, f"=F{last+1}/B{last+1}"])
st.append([])
st.append(["Not sampled: 158 'needs review' jobs the AI had not read yet when the snapshot was frozen (hidden from the site, waiting for the next AI run)."])
st.append(["Population counts are from the frozen snapshot (snapshot_2026-11-19.json, active non-duplicate jobs)."])
style_header(st)
for c in st[last + 1] + st[last + 2]:
    c.font = BOLD
for r in range(2, last + 3):
    st.cell(r, 5).number_format = "0.0%"
    st.cell(r, 6).number_format = "0.0"
widths(st, [34, 16, 10, 12, 11, 12])
WEIGHTED = f"Strata!$E${last+2}"

# ---------------- Token calls ----------------
tk = wb.create_sheet("Token calls")
tk.append(["Real Gemini calls (same system instruction, schema, temperature 0 as production)"])
tk.append(["job_id", "prompt_tokens (incl. system + schema)", "output_tokens", "thinking_tokens", "total_tokens", "latency_s", "response JSON"])
calls = [c for c in usage["calls"] if "error" not in c]
for c in calls:
    tk.append([c["id"], c["prompt_tokens"], c["output_tokens"], c["thinking_tokens"] or 0, c["total_tokens"], c["latency_s"], c["response"]])
cl = 2 + len(calls)
tk.append(["Mean", f"=AVERAGE(B3:B{cl})", f"=AVERAGE(C3:C{cl})", f"=AVERAGE(D3:D{cl})", f"=AVERAGE(E3:E{cl})", f"=AVERAGE(F3:F{cl})"])
for c in tk[cl + 1]:
    c.font = BOLD
    if c.column in (2, 3, 4, 5, 6):
        c.number_format = "0"
style_header(tk, 2)
tk["A1"].font = BOLD
tk.append([])
tk.append([f"Model: {usage['model']}. Source: response.usage_metadata from google-genai. Script: eval/measure_tokens.py"])
tk.append([f"count_tokens over all 50 sampled posts (user turn only, no system/schema): mean "
           f"{sum(c['prompt_tokens'] for c in usage['count_tokens'] if 'prompt_tokens' in c) / len(usage['count_tokens']):.0f} tokens; system instruction alone: {usage['system_instruction_tokens']} tokens"])
for row in tk.iter_rows(min_row=3, max_row=cl):
    row[6].alignment = Alignment(wrap_text=False)
widths(tk, [10, 18, 14, 14, 12, 10, 90])
TOK_IN, TOK_OUT, TOK_THINK = f"'Token calls'!$B${cl+1}", f"'Token calls'!$C${cl+1}", f"'Token calls'!$D${cl+1}"

# ---------------- Cost ----------------
co = wb.create_sheet("Cost")
ai_seen = sum(1 for j in snapshot if j["enrichment"] or j["eligibility"] != "rejected" or j["classified_by"] == "ai")
data = [
    ("Inputs", None, None),
    ("Input price, $ per 1M tokens (Gemini 3.5 Flash-Lite, standard)", 0.30, "Source: ai.google.dev/gemini-api/docs/pricing (checked 2026-11-19)"),
    ("Output price, $ per 1M tokens (includes thinking)", 2.50, "Same source"),
    ("Batch API discount", 0.5, "Batch tier is $0.15 / $1.25, i.e. 50% off. Same source"),
    ("Mean input tokens per post (measured)", f"={TOK_IN}", "Token calls tab"),
    ("Mean output tokens per post (measured)", f"={TOK_OUT}", "Token calls tab"),
    ("Mean thinking tokens per post (measured)", f"={TOK_THINK}", "No thinking used by this model/config"),
    ("India postings in snapshot", len(snapshot), "Active, non-duplicate jobs"),
    ("...of which the rules did not reject (the only ones sent to AI)", ai_seen, "Rejected jobs never reach Gemini"),
    ("All postings fetched per run (all locations)", 11861, "Run report, ingestion run 2/3"),
    ("Jobs new or changed on a normal daily refresh", 1, "Run 3: new 0, updated 1. Unchanged jobs reuse the stored AI result"),
    (None, None, None),
    ("Outputs", None, None),
    ("Cost per AI call ($)", "=B6/1000000*B3+(B7+B8)/1000000*B4", ""),
    ("Cost per 1,000 posts the AI reads ($)", "=B15*1000", "Headline number"),
    ("Same, with the Batch API ($)", "=B16*B5", "Daily refresh is not latency sensitive, so batch fits"),
    ("Share of India postings sent to AI", "=B10/B9", "Rules screen out the rest for free"),
    ("Cost per 1,000 India postings ingested ($)", "=B16*B18", ""),
    ("Cost per 1,000 postings fetched, all locations ($)", "=B16*B10/B11", ""),
    ("Cost of one full first-time run over today's catalogue ($)", "=B15*B10", ""),
    ("Cost of a normal daily refresh ($)", "=B15*B12", ""),
    ("Actually paid during the build ($)", 0, "Free tier (rate-limited), no billing enabled"),
]
co.append(["Item", "Value", "Note / source"])
for d in data:
    co.append(list(d))
style_header(co)
for r in range(2, co.max_row + 1):
    a = co.cell(r, 1)
    if a.value in ("Inputs", "Outputs"):
        a.font = BOLD
    v = co.cell(r, 2)
    if isinstance(v.value, (int, float)):
        v.font = INPUT
fmt = {3: "$0.00", 4: "$0.00", 5: "0%", 6: "0", 7: "0", 8: "0", 9: "#,##0", 10: "#,##0", 11: "#,##0", 12: "0",
       15: "$0.000000", 16: "$0.00", 17: "$0.00", 18: "0.0%", 19: "$0.000", 20: "$0.0000", 21: "$0.000", 22: "$0.000000", 23: "$0.00"}
for r, f in fmt.items():
    co.cell(r, 2).number_format = f
co["A16"].font = BOLD
co["B16"].font = BOLD
widths(co, [58, 14, 80])

# ---------------- Summary ----------------
su = wb.create_sheet("Summary", 0)
H = "'Hand-check (50)'!"
dc = f"{H}${col['decision_correct']}$2:${col['decision_correct']}${N}"
def field(k):
    rng = f"{H}${col[k]}$2:${col[k]}${N}"
    return (f"=COUNTIF({rng},\"Y\")/(COUNTA({rng})-COUNTIF({rng},\"-\"))",
            f"=COUNTIF({rng},\"N\")", f"=COUNTIF({rng},\"U\")")
su.append(["RiseFirst: AI tagging accuracy and cost", None, None])
su.append(["Hand-check of 50 posts from the 2026-11-19 snapshot. Model: gemini-3.5-flash-lite. All figures are formulas over the other tabs.", None, None])
su.append([])
su.append(["Fresher decision (shown on site vs hidden)", "Value", "How to read it"])
su.append(["Correct in the 50-post sample", f"=COUNTIF({dc},\"Y\")/COUNTA({dc})", "Sample is stratified, so AI decisions are over-represented on purpose"])
su.append(["Population-weighted accuracy", f"={WEIGHTED}", "Re-weights each stratum by its real size (Strata tab)"])
sh = f"{H}${col['shown_on_site']}$2:${col['shown_on_site']}${N}"
su.append(["Precision of the published list (sample)", f"=COUNTIFS({sh},\"yes\",{dc},\"Y\")/COUNTIF({sh},\"yes\")", "Of the jobs shown, how many are genuine fresher roles"])
by = f"{H}${col['decided_by']}$2:${col['decided_by']}${N}"
su.append(["When AI made the final call", f"=COUNTIFS({by},\"ai\",{dc},\"Y\")/COUNTIF({by},\"ai\")", "AI decided 17 of the 50 rows"])
su.append(["When rules made the final call", f"=COUNTIFS({by},\"rules\",{dc},\"Y\")/COUNTIF({by},\"rules\")", "Rules decided 33 of the 50 rows"])
sr = f"{H}${col['strict_reading_correct']}$2:${col['strict_reading_correct']}${N}"
su.append(["Correct on a strict reading (fresher = no experience required)", f"=COUNTIF({sr},\"Y\")/COUNTA({sr})", "Treats '1+ years required' as not fresher. Flips 6 rows"])
su.append(["False positives (shown, should be hidden)", f"=COUNTIF({H}${col['error_type']}$2:${col['error_type']}${N},\"False positive*\")", "Both are AI calls on posts with no years stated"])
su.append(["Missed (hidden, should be shown)", f"=COUNTIF({H}${col['error_type']}$2:${col['error_type']}${N},\"Missed*\")", "AI was stricter than the 0-1 year definition on '1+ years' posts"])
su.append([])
su.append(["Field tags", "Correct", "Wrong", "Left unknown"])
for label, k in [("Category", "category_ok"), ("Employment type", "employment_type_ok"), ("Work mode", "work_mode_ok"),
                 ("Location / city", "location_ok"), ("Experience range", "experience_ok"), ("Skills (AI-tagged rows only)", "skills_ok")]:
    su.append([label, *field(k)])
su.append([])
su.append(["Cost", "Value", ""])
su.append(["Per 1,000 posts the AI reads", "=Cost!B16", "Measured tokens x list price"])
su.append(["Per 1,000 posts with the Batch API", "=Cost!B17", ""])
su.append(["Per 1,000 India posts ingested (rules filter first)", "=Cost!B19", ""])
su.append(["Normal daily refresh", "=Cost!B22", "Unchanged jobs are never re-sent"])
su.append([])
su.append(["Main error sources found by the hand-check"])
for t in [
    "1. Work mode: a city in the location defaults to 'onsite' and wins over the AI's or the description's 'hybrid' (5 of 6 work-mode errors).",
    "2. Category: rules use the first matching word in the title ('Finance Content Creator' -> Finance, 'Account Director' -> Other).",
    "3. AI publishes some posts that state no years at all (2 of 8 AI-published). Fix: require an explicit fresher signal before AI can publish.",
    "4. Employment type is 'unknown' for 30% of rows: Greenhouse boards don't send it and the AI only runs on the uncertain middle.",
]:
    su.append([t])
su["A1"].font = Font(name=FONT, bold=True, size=14)
for r in (4, 14, 22, 28):
    for c in su[r]:
        if c.value:
            c.font = Font(name=FONT, bold=True, color="FFFFFF")
            c.fill = HEAD
for r in range(5, 11):
    su.cell(r, 2).number_format = "0.0%"
for r in range(15, 21):
    su.cell(r, 2).number_format = "0%"
for r in range(23, 27):
    su.cell(r, 2).number_format = "$0.000"
su["B11"].number_format = "0"
su["B12"].number_format = "0"
widths(su, [62, 12, 14, 64])

# ---------------- Pipeline runs ----------------
pr = wb.create_sheet("Pipeline runs")
pr.append(["run", "started (UTC)", "fetched", "india", "eligible", "review", "rejected", "ai_calls", "ai_failures", "ai_cache_hits", "ai_skipped", "model", "what happened"])
for r in runs:
    pr.append(list(r))
style_header(pr)
widths(pr, [5, 17, 9, 7, 8, 8, 8, 8, 10, 12, 10, 22, 80])

# ---------------- Prompts & AI tools ----------------
pt = wb.create_sheet("Prompts & AI tools")
pt.append(["Item", "Content"])
user_tpl = ("Company: {company}\nTitle: {title}\nLocation: {location_text}\n<posting>\n{description[:%d]}\n</posting>" % _MAX_DESCRIPTION_CHARS)
for item, content in [
    ("AI tools used", "Gemini 3.5 Flash-Lite via google-genai SDK: runtime tagging in the product (gemini-3.5-flash for the first runs until its free quota ran out).\n"
                      "Claude Code (Claude Opus 5.5): architecture, code, tests, the sourcing spike, and a first-pass read of the 50 hand-check posts with evidence quotes, which I then verified."),
    ("Prompt version", PROMPT_VERSION),
    ("System instruction", SYSTEM_INSTRUCTION),
    ("User turn template", user_tpl),
    ("Generation config", "response_mime_type=application/json, response_schema=<schema below>, temperature=0, no tools"),
    ("Output JSON schema (Pydantic, validated again after the call)", json.dumps(schema, indent=1)),
    ("How the answer is used", "Only for jobs the rules did not reject. Confidence < 0.7 is ignored. AI can promote 'needs review' to eligible or rejected, "
                               "and can demote a rules-eligible job to review; it can never un-reject. Code: backend/src/risefirst/domain/eligibility.py (combine_with_ai)"),
    ("Hand-check rubric", "Fresher = brief's definition, 0-1 years. FIT: intern/trainee/graduate, freshers welcome, experience only preferred, or stated minimum <= 1 year. "
                          "NOT: 2+ years or substantial experience required. UNCLEAR: no signal, so hiding it is correct. Decision correct = shown on site iff FIT."),
    ("Reproduce", "eval/sample.py (seeded sample) -> eval/judgments.py (verdicts) -> eval/score.py (scores, hand_check.csv) -> eval/measure_tokens.py (tokens) -> eval/build_sheet.py (this file)"),
]:
    pt.append([item, content])
style_header(pt)
for row in pt.iter_rows(min_row=2):
    row[0].font = BOLD
    row[1].alignment = WRAP
    row[0].alignment = WRAP
widths(pt, [30, 120])

for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            f = c.font
            c.font = Font(name=FONT, bold=f.bold, italic=f.italic, size=f.size, color=f.color)
wb.save("RiseFirst_eval.xlsx")
print("saved")
