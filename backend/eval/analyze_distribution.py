import json
import pandas as pd
from pathlib import Path

results_path = Path("eval/results.json")
golden_path = Path("eval/data/golden_dataset.json")
if not golden_path.exists():
    golden_path = Path("eval/golden_dataset.json")

with open(results_path, encoding="utf-8") as f:
    results = json.load(f)

with open(golden_path, encoding="utf-8") as f:
    golden_data = json.load(f)
    golden = {str(g["pair_id"]): g for g in golden_data}

rows = []
for r in results:
    pid = str(r["pair_id"])
    human = golden[pid]["human_decision"]
    # Handle both r["ai_score"] and r["decision"]["score"]
    if "ai_score" in r:
        ai_score = r["ai_score"]
    elif isinstance(r.get("decision"), dict) and "score" in r["decision"]:
        ai_score = r["decision"]["score"]
    else:
        ai_score = 0
    rows.append({"pair_id": pid, "score": ai_score, "human": human})

df = pd.DataFrame(rows)
print("="*60)
print("SCORE DISTRIBUTION BY HUMAN DECISION:")
print("="*60)
print(df.groupby("human")["score"].describe())

print("\n" + "="*60)
print("PERCENTILES BY HUMAN DECISION:")
print("="*60)
for h in ["REJECT", "ESCALATE", "ADVANCE"]:
    subset = df[df["human"] == h]["score"]
    print(f"\n[{h}] (N={len(subset)}):")
    print(f"  Min: {subset.min()}, 10%: {subset.quantile(0.10):.1f}, 25%: {subset.quantile(0.25):.1f}, Median: {subset.median():.1f}, 75%: {subset.quantile(0.75):.1f}, 90%: {subset.quantile(0.90):.1f}, Max: {subset.max()}")

print("\n" + "="*60)
print("FULL DISTRIBUTION (SORTED BY SCORE):")
print("="*60)
pd.set_option('display.max_rows', 250)
print(df.sort_values("score")[["pair_id", "score", "human"]].to_string(index=False))
