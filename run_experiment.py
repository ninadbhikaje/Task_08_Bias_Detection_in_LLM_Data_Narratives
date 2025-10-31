# run_experiment.py
import os
import time
import json
import uuid
import argparse
from pathlib import Path
from datetime import datetime

# ---------- Optional real API clients ----------
def call_openai(prompt, temperature=0.3, model="gpt-4o-mini"):
    """
    Requires: pip install openai
    Env: OPENAI_API_KEY
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": "You are an analytical, concise assistant. Ground your answer only in the provided data."},
            {"role": "user", "content": prompt}
        ],
    )
    return resp.choices[0].message.content.strip()

def call_anthropic(prompt, temperature=0.3, model="claude-3-sonnet-20240229"):
    """
    Requires: pip install anthropic
    Env: ANTHROPIC_API_KEY
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY")
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        temperature=temperature,
        max_tokens=800,
        system="You are an analytical, concise assistant. Ground your answer only in the provided data.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

def call_gemini(prompt, temperature=0.3, model="gemini-1.5-pro"):
    """
    Requires: pip install google-generativeai
    Env: GOOGLE_API_KEY
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY")
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(model)
    resp = gmodel.generate_content(prompt, generation_config={"temperature": temperature})
    return resp.text.strip() if resp and resp.text else ""

# ---------- Mock model (no API needed) ----------
import random
def call_mock(prompt, temperature=0.3, model="mock-llm"):
    """
    Deterministic-ish mock to test the pipeline end-to-end without API keys.
    It varies tone/keywords using prompt cues to simulate bias patterns.
    """
    base_lines = [
        "Based on the provided statistics, improvements in defensive clears and possession are likely to yield wins.",
        "Close-game losses suggest marginal gains will help; consider situational defense and clearing under pressure.",
    ]
    offense_focus = "Focus on generating high-quality shots and playmaking in settled offense."
    defense_focus = "Focus on defensive coordination, clearing under pressure, and goalie-led transitions."
    balanced = "A balanced approach is prudent: continue offensive efficiency while addressing clearing gaps."

    text = random.choice(base_lines)
    if "struggling" in prompt.lower() or "what went wrong" in prompt.lower():
        text = "The data indicate issues under pressure; turnovers and clears likely constrained outcomes. " + defense_focus
    if "developing" in prompt.lower() or "opportunities" in prompt.lower():
        text = "The data show strong potential; small improvements could lead to breakthroughs. " + balanced
    if "faceoff performance caused losses" in prompt.lower():
        text += " Faceoffs appear influential, but verification against exact win rates is needed."

    # Player mention heuristic
    players = ["Player A", "Player B", "Player C", "Player D", "Player E"]
    mention = random.choice(players + players + [""])  # bias toward mentioning a player
    if mention:
        text += f" Consider targeted coaching for {mention}."

    return text

# ---------- Model registry ----------
MODEL_REGISTRY = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "mock": call_mock,  # default if no keys
}

def list_prompts(prompt_dir: Path):
    files = sorted([p for p in prompt_dir.glob("*.txt") if p.is_file()])
    # Infer hypothesis + variant from filename like H1_positive.txt
    items = []
    for p in files:
        name = p.stem
        if "_" in name:
            hypothesis, variant = name.split("_", 1)
        else:
            hypothesis, variant = name, "default"
        items.append({"path": p, "hypothesis": hypothesis, "variant": variant})
    return items

def main():
    parser = argparse.ArgumentParser(description="Run LLM bias experiment and log results.")
    parser.add_argument("--prompt_dir", type=str, default="prompts", help="Directory of prompt .txt files")
    parser.add_argument("--results", type=str, default="results/raw_responses.jsonl", help="Output JSONL log path")
    parser.add_argument("--models", type=str, nargs="+", default=["mock"], help="Models: mock, openai, anthropic, gemini")
    parser.add_argument("--runs", type=int, default=3, help="Samples per prompt per model")
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--openai_model", type=str, default="gpt-4o-mini")
    parser.add_argument("--anthropic_model", type=str, default="claude-3-sonnet-20240229")
    parser.add_argument("--gemini_model", type=str, default="gemini-1.5-pro")
    args = parser.parse_args()

    prompt_dir = Path(args.prompt_dir)
    out_path = Path(args.results)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompts = list_prompts(prompt_dir)
    if not prompts:
        raise SystemExit(f"No prompts found in {prompt_dir}. Add files like H1_positive.txt, H1_negative.txt, etc.")

    model_args = {
        "openai": {"model": args.openai_model},
        "anthropic": {"model": args.anthropic_model},
        "gemini": {"model": args.gemini_model},
        "mock": {"model": "mock-llm"},
    }

    with out_path.open("a", encoding="utf-8") as f:
        for pr in prompts:
            prompt_text = pr["path"].read_text(encoding="utf-8")
            for m in args.models:
                caller = MODEL_REGISTRY.get(m)
                if caller is None:
                    print(f"[WARN] Unknown model key: {m}. Skipping.")
                    continue
                for i in range(args.runs):
                    try:
                        response = caller(prompt_text, temperature=args.temperature, **model_args[m])
                    except Exception as e:
                        response = f"[ERROR] {type(e).__name__}: {e}"

                    record = {
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.utcnow().isoformat(),
                        "model": m,
                        "model_version": model_args[m]["model"],
                        "temperature": args.temperature,
                        "hypothesis": pr["hypothesis"],
                        "variant": pr["variant"],
                        "prompt_path": str(pr["path"]),
                        "prompt_text": prompt_text,
                        "response_text": response,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    time.sleep(0.2)  # polite pacing
                    print(f"[OK] {pr['hypothesis']} / {pr['variant']} / {m} run {i+1}")

if __name__ == "__main__":
    main()
