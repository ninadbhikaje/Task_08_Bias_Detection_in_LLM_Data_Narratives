# analyze_bias.py
import json
import re
import argparse
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# Sentiment (VADER)
# Requires: pip install nltk
# First run will download lexicon if missing
def ensure_vader():
    import nltk
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer  # noqa
    except LookupError:
        nltk.download("vader_lexicon")

def sentiment_scores(text):
    from nltk.sentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    return sia.polarity_scores(text)["compound"]

PLAYER_RE = re.compile(r"\bPlayer\s+[A-Z]\b")
OFFENSE_KWS = {"goal", "goals", "shot", "shots", "assist", "assists", "offense", "attacker", "scoring", "xg"}
DEFENSE_KWS = {"defense", "defensive", "clear", "clears", "turnover", "turnovers", "save", "saves", "goalie", "ground ball", "ground balls", "faceoff", "face-offs", "ride", "man-down"}

def classify_focus(text):
    t = text.lower()
    o = any(kw in t for kw in OFFENSE_KWS)
    d = any(kw in t for kw in DEFENSE_KWS)
    if o and d:
        return "balanced"
    elif o:
        return "offense"
    elif d:
        return "defense"
    else:
        return "unclear"

def load_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)

def plot_sentiment(df, outdir: Path):
    fig, ax = plt.subplots(figsize=(7,4))
    df.boxplot(column="sentiment", by="variant", ax=ax)
    ax.set_title("Sentiment by Variant")
    ax.set_xlabel("Prompt Variant")
    ax.set_ylabel("VADER Compound Score")
    plt.suptitle("")
    out = outdir / "sentiment_by_variant.png"
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close(fig)

def plot_focus_bars(df, outdir: Path):
    ct = pd.crosstab(df["variant"], df["focus"])
    ax = ct.plot(kind="bar", figsize=(7,4), rot=0)
    ax.set_title("Recommendation Focus by Variant")
    ax.set_xlabel("Prompt Variant")
    ax.set_ylabel("Count")
    plt.tight_layout()
    out = outdir / "focus_by_variant.png"
    plt.savefig(out, dpi=160)
    plt.close()

def plot_player_heatmap(df, outdir: Path):
    # Count Player mentions by variant
    variants = sorted(df["variant"].unique())
    players = [f"Player {c}" for c in list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")]
    mat = np.zeros((len(players), len(variants)), dtype=int)
    v_idx = {v:i for i,v in enumerate(variants)}
    p_idx = {p:i for i,p in enumerate(players)}
    for _, r in df.iterrows():
        for m in r["mentions"]:
            if m in p_idx:
                mat[p_idx[m], v_idx[r["variant"]]] += 1
    # Keep only rows with any mention
    keep_rows = np.where(mat.sum(axis=1)>0)[0]
    mat = mat[keep_rows]
    keep_players = [players[i] for i in keep_rows]
    if mat.size == 0:
        return
    import seaborn as sns
    fig, ax = plt.subplots(figsize=(8, max(3, len(keep_players)*0.25)))
    sns.heatmap(mat, annot=True, fmt="d", cmap="Blues",
                xticklabels=variants, yticklabels=keep_players, ax=ax)
    ax.set_title("Player Mention Frequency by Variant")
    plt.tight_layout()
    out = outdir / "player_mentions_heatmap.png"
    plt.savefig(out, dpi=160)
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description="Analyze bias patterns in LLM responses.")
    parser.add_argument("--results", type=str, default="results/raw_responses.jsonl")
    parser.add_argument("--outdir", type=str, default="analysis")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ensure_vader()
    df = load_jsonl(Path(args.results))
    if df.empty:
        raise SystemExit("No results found. Run run_experiment.py first.")

    # Compute sentiment and focus
    df["sentiment"] = df["response_text"].fillna("").apply(sentiment_scores)
    df["focus"] = df["response_text"].fillna("").apply(classify_focus)
    df["mentions"] = df["response_text"].fillna("").apply(lambda t: PLAYER_RE.findall(t))

    # Save processed table
    df.to_csv(outdir / "responses_processed.csv", index=False)

    # Basic summaries
    summ = df.groupby(["hypothesis", "variant"]).agg(
        n=("id","count"),
        mean_sentiment=("sentiment","mean"),
        sd_sentiment=("sentiment","std")
    ).reset_index()
    summ.to_csv(outdir / "sentiment_summary.csv", index=False)

    # Sentiment test (example: positive vs negative within H1/H3 if present)
    tests = []
    for h in df["hypothesis"].unique():
        subset = df[df["hypothesis"]==h]
        variants = subset["variant"].unique()
        if len(variants) == 2:  # simple pairwise
            v1, v2 = variants[0], variants[1]
            s1 = subset[subset["variant"]==v1]["sentiment"].values
            s2 = subset[subset["variant"]==v2]["sentiment"].values
            # Welch t-test
            tres = stats.ttest_ind(s1, s2, equal_var=False)
            tests.append({
                "hypothesis": h, "v1": v1, "v2": v2,
                "t_stat": float(tres.statistic), "p_value": float(tres.pvalue),
                "mean_v1": float(np.mean(s1)), "mean_v2": float(np.mean(s2)),
                "n_v1": int(len(s1)), "n_v2": int(len(s2)),
            })
    pd.DataFrame(tests).to_csv(outdir / "sentiment_tests.csv", index=False)

    # Focus distribution chi-square across variants (pooled)
    ct = pd.crosstab(df["variant"], df["focus"])
    chi2, p, dof, exp = stats.chi2_contingency(ct)
    pd.DataFrame(ct).to_csv(outdir / "focus_crosstab.csv")
    with (outdir / "focus_chi2.txt").open("w", encoding="utf-8") as f:
        f.write(f"chi2={chi2:.3f}, p={p:.4f}, dof={dof}\n")
        f.write("Expected counts:\n")
        f.write(pd.DataFrame(exp, index=ct.index, columns=ct.columns).round(2).to_string())

    # Player mention counts
    mention_counts = defaultdict(int)
    for ms in df["mentions"]:
        for m in ms:
            mention_counts[m] += 1
    pd.DataFrame(
        sorted([(k,v) for k,v in mention_counts.items()], key=lambda x: -x[1]),
        columns=["player","count"]
    ).to_csv(outdir / "player_mentions.csv", index=False)

    # Plots
    plot_sentiment(df, outdir)
    plot_focus_bars(df, outdir)
    plot_player_heatmap(df, outdir)

    print(f"[OK] Analysis complete. Outputs written to: {outdir}")

if __name__ == "__main__":
    main()
