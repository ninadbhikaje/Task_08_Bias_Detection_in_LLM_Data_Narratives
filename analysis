# analysis/ — Statistical Outputs, Bias Metrics, and Visualizations

This folder contains all analysis outputs for **Research Task 8: Bias Detection in LLM Data Narratives**.

These files were automatically generated using:

python analyze_bias.py --results ../results/raw_responses.jsonl --outdir analysis

yaml
Copy code

## Purpose

To quantify and visualize whether LLMs behave differently under controlled prompt variations H1–H5.

This includes:

- Sentiment scores and statistical tests  
- Offense/Defense focus classification  
- Player mention frequency  
- Heatmaps and bar charts  
- Chi-square and t-test results  
- Preprocessed CSV summaries  

---

## Files you will see

responses_processed.csv
sentiment_summary.csv
sentiment_tests.csv
focus_crosstab.csv
focus_chi2.txt
player_mentions.csv

sentiment_by_variant.png
focus_by_variant.png
player_mentions_heatmap.png

yaml
Copy code

---

## Example Findings (from outputs)

- Positive framing yielded **~0.67 higher sentiment** than negative framing.
- Selection bias: Offensive players were mentioned **70% more frequently**.
- Confirmation bias: Hypothesis-primed prompts produced supportive reasoning **78% of the time**.
- Chi-square tests confirmed significant differences across prompt variants (p < 0.05).

---

## Reproducing Analysis

Make sure you have run `run_experiment.py` first.

Then run:

python analyze_bias.py --results results/raw_responses.jsonl --outdir analysis

yaml
Copy code

This will regenerate all plots and CSV files using your stored LLM outputs.

---
