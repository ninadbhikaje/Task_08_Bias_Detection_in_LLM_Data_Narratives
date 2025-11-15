import json
import argparse
from pathlib import Path
import re
import csv

GROUND_TRUTH = {
    "Player A": {"goals": 45, "assists": 20, "turnovers": 10},
    "Player B": {"goals": 38, "assists": 35, "turnovers": 8},
    "Player C": {"goals": 22, "assists": 40, "turnovers": 6},
    "Player D": {"goals": 14, "assists": 15, "turnovers": 5},
    "Player E": {"saves": 198, "gaa": 11.0},

    "team_record": "12-6",
    "clear_pct": 87.1,
    "faceoff_pct": 53.0
}

NUM_RE = re.compile(r"(\d+\.?\d*)")

def extract_numbers(text):
    return [float(n) for n in NUM_RE.findall(text)]

def validate_text(text):
    issues = []

    # Check player numbers
    for player, stats in GROUND_TRUTH.items():
        for stat_name, stat_val in stats.items():
            if isinstance(stat_val, (int, float)):
                if str(stat_val) not in text:
                    # Only warn, do not error; many prompts don't require repeating all stats
                    continue

            # Detect hallucinated numbers for players
            nums = extract_numbers(text)
            for n in nums:
                # If wildly outside known stat ranges, flag
                if n > 500 and "save" not in text.lower():
                    issues.append(f"Unusual number detected ({n}) outside ground-truth ranges.")

    # Check team record
    if "12" not in text or "6" not in text:
        if "record" in text.lower():
            issues.append("Possible team record discrepancy.")

    return issues

def main():
    parser = argparse.ArgumentParser(description="Validate LLM responses against ground truth.")
    parser.add_argument("--results", type=str, default="results/raw_responses.jsonl")
    parser.add_argument("--out", type=str, default="results/validation_report.csv")
    args = parser.parse_args()

    path = Path(args.results)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            issues = validate_text(rec["response_text"])
            rows.append({
                "id": rec["id"],
                "model": rec["model"],
                "hypothesis": rec["hypothesis"],
                "variant": rec["variant"],
                "issues": "; ".join(issues) if issues else "None"
            })

    # Save CSV
    with out.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Validation complete → {out}")

if __name__ == "__main__":
    main()
