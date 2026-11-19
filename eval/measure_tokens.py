"""Measure real Gemini token usage for the production prompt. Runs inside the worker container:
   docker compose cp eval/. worker:/tmp/eval && docker compose exec worker python /tmp/eval/measure_tokens.py
"""
import json, os, time
from google import genai
from google.genai import types
from risefirst.infrastructure.llm.gemini import SYSTEM_INSTRUCTION, _GeminiOutput, _MAX_DESCRIPTION_CHARS

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, response_mime_type="application/json",
                                     response_schema=_GeminiOutput, temperature=0)

def prompt(j):  # identical to GeminiEnricher.enrich
    return (f"Company: {j['company']}\nTitle: {j['title']}\nLocation: {j['location_text']}\n"
            f"<posting>\n{j['description'][:_MAX_DESCRIPTION_CHARS]}\n</posting>")

sample = json.load(open("/tmp/eval/sample50.json"))
out = {"model": MODEL, "count_tokens": [], "calls": []}
for j in sample:  # input size of every sampled post (system instruction counted separately below)
    try:
        r = client.models.count_tokens(model=MODEL, contents=prompt(j))
        out["count_tokens"].append({"id": j["id"], "prompt_tokens": r.total_tokens, "desc_chars": len(j["description"])})
    except Exception as e:
        out["count_tokens"].append({"id": j["id"], "error": str(e)[:200]})
try:
    out["system_instruction_tokens"] = client.models.count_tokens(model=MODEL, contents=SYSTEM_INSTRUCTION).total_tokens
except Exception as e:
    out["system_instruction_tokens"] = str(e)[:200]

for j in sample[::5][:10]:  # 10 real calls, spread across strata
    t0 = time.time()
    try:
        r = client.models.generate_content(model=MODEL, contents=prompt(j), config=config)
        u = r.usage_metadata
        out["calls"].append({"id": j["id"], "latency_s": round(time.time() - t0, 2),
            "prompt_tokens": u.prompt_token_count, "output_tokens": u.candidates_token_count,
            "thinking_tokens": u.thoughts_token_count, "total_tokens": u.total_token_count,
            "response": r.text})
    except Exception as e:
        out["calls"].append({"id": j["id"], "error": str(e)[:300]})
    json.dump(out, open("/tmp/eval/token_usage.json", "w"), indent=1)
    time.sleep(15)
print(json.dumps({k: v for k, v in out.items() if k != "count_tokens"}, indent=1)[:4000])
