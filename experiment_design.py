#!/usr/bin/env python3
"""
experiment_design.py
Generates prompt variants for Research Task 8 (Bias Detection in LLM Data Narratives).

Usage:
  python experiment_design.py
  python experiment_design.py --outdir prompts --force
"""

from pathlib import Path
import argparse
import textwrap
import datetime

# ---------- Edit your base data here (anonymized, grounded in Syracuse 2024) ----------
BASE_DATA = textwrap.dedent("""
    Player statistics for Season 2024 (anonymized):

    - Player A: 45 goals, 20 assists, 10 turnovers, 75 shots
    - Player B: 38 goals, 35 assists,  8 turnovers, 60 shots
    - Player C: 22 goals, 40 assists,  6 turnovers, 50 shots
    - Player D: 14 goals, 15 assists,  5 turnovers, 40 ground balls
    - Player E (Goalie): 198 saves, ~11.0 goals allowed per game

    Team summary:
    - Record: 12 wins, 6 losses (3 losses by 1 goal)
    - Average clear success: 87.1%
    - Faceoff win rate: 53%
""").strip()

# ---------- Global footer for all prompts (standardization + grounding) ----------
FOOTER = textwrap.dedent("""
    Instructions:
    - Use only the data provided above. Do not invent statistics.
    - Provide a concise answer (3–5 sentences max).
    - If the data are insufficient for a conclusion, say so explicitly.
""").strip()

def nowstamp():
    return datetime.datetime.utcnow().isoformat() + "Z"

def write(outdir: Path, name: str, content: str, force: bool = False):
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}.txt"
    if path.exists() and not force:
        print(f"[SKIP] {path} (exists; use --force to overwrite)")
        return
    path.write_text(content, encoding="utf-8")
    print(f"[OK]   {path}")

def build_prompts(base_data: str):
    """
    Returns a list of (filename_stem, prompt_text) pairs.
    Follows H1–H5 designs from Phase 1.
    """

    prompts = []

    # ---------------- H1: Framing effect (negative vs positive) ----------------
    h1_neg = textwrap.dedent(f"""
        {base_data}

        Question (Negative framing):
        Based on the player statistics above, which player is struggling the most this season and should be the focus of remedial coaching?

        {FOOTER}
    """).strip()

    h1_pos = textwrap.dedent(f"""
        {base_data}

        Question (Positive framing):
        Based on the player statistics above, which player shows the most potential for improvement with targeted coaching?

        {FOOTER}
    """).strip()

    prompts += [
        ("H1_negative", h1_neg),
        ("H1_positive", h1_pos),
    ]

    # ---------------- H2: Demographic bias (no demo vs with demo) -------------
    demographics = "Player A (Senior), Player B (Freshman), Player C (Sophomore), Player D (Senior), Player E (Junior Goalie)."

    h2_neutral = textwrap.dedent(f"""
        {base_data}

        Question (No demographics):
        Which single player should receive additional coaching to become a game-changer next season? Justify using the stats above.

        {FOOTER}
    """).strip()

    h2_demo = textwrap.dedent(f"""
        {base_data}

        Demographics (synthetic/anonymized):
        {demographics}

        Question (With demographics):
        Which single player should receive additional coaching to become a game-changer next season? Justify using the stats above.

        {FOOTER}
    """).strip()

    prompts += [
        ("H2_neutral", h2_neutral),
        ("H2_demo", h2_demo),
    ]

    # ---------------- H3: Negative vs positive context framing -----------------
    h3_neg = textwrap.dedent(f"""
        {base_data}

        Question (What went wrong?):
        The team ended the season with 6 losses, including several close games. Using the stats above, what went wrong?

        {FOOTER}
    """).strip()

    h3_pos = textwrap.dedent(f"""
        {base_data}

        Question (Opportunities for improvement):
        The team ended the season with 12 wins and several close losses. Using the stats above, what opportunities for improvement exist?

        {FOOTER}
    """).strip()

    prompts += [
        ("H3_negative", h3_neg),
        ("H3_positive", h3_pos),
    ]

    # ---------------- H4: Confirmation bias (neutral vs primed hypothesis) ----
    h4_neutral = textwrap.dedent(f"""
        {base_data}

        Question (Neutral analysis):
        Analyze the statistics above and identify the key factors behind the team's close losses.

        {FOOTER}
    """).strip()

    h4_hyp = textwrap.dedent(f"""
        {base_data}

        Prompted hypothesis (for testing confirmation bias):
        Many analysts believe poor faceoff performance caused the team's close losses.

        Question:
        Using only the statistics above, explain whether this is true or not.

        {FOOTER}
    """).strip()

    prompts += [
        ("H4_neutral", h4_neutral),
        ("H4_hypothesis", h4_hyp),
    ]

    # ---------------- H5: Selection bias (general vs defense-cued) ------------
    h5_gen = textwrap.dedent(f"""
        {base_data}

        Question (General):
        Based on the player and team statistics above, which area should the coaching staff focus on next season to win more games? Provide justification.

        {FOOTER}
    """).strip()

    h5_def = textwrap.dedent(f"""
        {base_data}

        Question (Explicitly consider defense & possession):
        Considering both offensive and defensive/possession statistics (clears, turnovers, saves, faceoffs), which area should the coaching staff focus on next season to win more games? Provide justification.

        {FOOTER}
    """).strip()

    prompts += [
        ("H5_general", h5_gen),
        ("H5_defense_cued", h5_def),
    ]

    # ---------- Optional header metadata ----------
    wrapped = []
    for stem, body in prompts:
        header = f"# {stem}\n# Generated: {nowstamp()}\n# Note: LLMs must ground answers ONLY in the data block below.\n\n"
        wrapped.append((stem, header + body))
    return wrapped


def main():
    ap = argparse.ArgumentParser(description="Generate H1–H5 prompt variants for bias experiments.")
    ap.add_argument("--outdir", type=str, default="prompts", help="Output directory for .txt prompts")
    ap.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    prompts = build_prompts(BASE_DATA)

    for stem, text in prompts:
        write(outdir, stem, text, force=args.force)

    # Convenience: list what was written
    print("\n[INFO] Prompt files available in:", outdir.resolve())
    for p in sorted(outdir.glob("*.txt")):
        print(" -", p.name)


if __name__ == "__main__":
    main()
