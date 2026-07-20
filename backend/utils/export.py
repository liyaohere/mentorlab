import json
import csv
from pathlib import Path


def main():
    runs_dir = "scripts/simulation_results/runs"

    input_file = f"{runs_dir}/run008_20260720_opus_across.jsonl"
    output_csv = f"{runs_dir}/problem_formulations_output.csv"

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    valid_records = [r for r in records if r.get("simulated_response")]

    headers = [
        "Profile ID",
        "Condition",
        "Input Tokens",
        "Output Tokens",
        "AI Diagnosis (Shown)",
        "Problem Formulation (Simulated Response)",
        "Response Word Count",
    ]

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for r in valid_records:
            pid = r.get("profile_id", "")
            cond = r.get("condition", "")
            inp_tokens = r.get("total_input_tokens", 0)
            out_tokens = r.get("total_output_tokens", 0)

            shown = r.get("result", {}).get("shown", "")
            if isinstance(shown, list):
                shown = "\n\n---\n\n".join(shown)

            response = r.get("simulated_response", "")
            word_count = len(response.split())

            writer.writerow(
                [pid, cond, inp_tokens, out_tokens, shown, response, word_count]
            )


if __name__ == "__main__":
    main()
