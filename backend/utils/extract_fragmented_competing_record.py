"""
inspect_malformed.py

抓取 run_simulation.py 输出的 .jsonl 里，competing 条件下
format compliance 检查未通过的记录，把完整的 shown 内容、
按 "---" 切分出的每一段文本、每段字数都打印出来，方便人工确认
是不是 summarizer 分段失败（比如某一段只有几个词，或缺失
CAUSE/PREDICTION/NEXT STEP）。

用法:
    python inspect_malformed.py --input path/to/runXXX.jsonl
    python inspect_malformed.py --input path/to/runXXX.jsonl --save malformed.json
    python inspect_malformed.py --input path/to/runXXX.jsonl --profile P101 P135
"""

import argparse
import json
import sys
from pathlib import Path


def load_results(path: str) -> list[dict]:
    results = []
    with open(path) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def word_count(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def check_format(text: str) -> dict:
    """与 analyze_simulation.py 里的 check_format 保持一致的判定逻辑。"""
    if not text:
        return {
            "has_cause": False,
            "has_prediction": False,
            "has_next_step": False,
            "compliant": False,
        }
    t = text.upper()
    has_cause = "CAUSE" in t
    has_prediction = "PREDICTION" in t
    has_next_step = "NEXT STEP" in t
    return {
        "has_cause": has_cause,
        "has_prediction": has_prediction,
        "has_next_step": has_next_step,
        "compliant": has_cause and has_prediction and has_next_step,
    }


def analyze_shown(shown) -> dict:
    """
    针对 competing 条件的 shown（应为 list[str]），逐段分析：
    - 段数是否为 3
    - 每段字数
    - 每段是否包含 CAUSE/PREDICTION/NEXT STEP
    - 整体是否合规（与 analyze_simulation.py 的判定一致：all(...)）
    """
    if isinstance(shown, list):
        parts = shown
    else:
        parts = [shown] if shown else []

    part_reports = []
    for i, p in enumerate(parts):
        fmt = check_format(p)
        part_reports.append(
            {
                "part_index": i,
                "word_count": word_count(p),
                "char_count": len(p or ""),
                "has_cause": fmt["has_cause"],
                "has_prediction": fmt["has_prediction"],
                "has_next_step": fmt["has_next_step"],
                "compliant": fmt["compliant"],
                "text": p,
            }
        )

    overall_compliant = len(parts) > 0 and all(
        check_format(p)["compliant"] for p in parts
    )

    return {
        "num_parts": len(parts),
        "expected_parts": 3,
        "parts_ok": len(parts) == 3,
        "overall_compliant": overall_compliant,
        "parts": part_reports,
    }


def main():
    parser = argparse.ArgumentParser(
        description="抓取 competing 条件下 format 不合规的记录，逐段展示"
    )
    parser.add_argument("--input", required=True, help=".jsonl 结果文件路径")
    parser.add_argument(
        "--condition",
        default="competing",
        help="要检查的条件 (默认 competing，因为目前只有这个条件观察到问题)",
    )
    parser.add_argument(
        "--profile",
        nargs="*",
        default=None,
        help="只看指定的 profile_id（不指定则检查全部）",
    )
    parser.add_argument(
        "--save",
        default=None,
        help="把结果保存成 json 文件（比如 malformed.json）方便存档/再分析",
    )
    parser.add_argument(
        "--full-text",
        action="store_true",
        help="打印每段完整文本（默认只打印前200字符预览）",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: 找不到文件 {args.input}")
        sys.exit(1)

    results = load_results(args.input)
    print(f"共加载 {len(results)} 条记录")

    targets = [
        r
        for r in results
        if r.get("condition") == args.condition and r.get("result", {}).get("shown")
    ]
    if args.profile:
        targets = [r for r in targets if r.get("profile_id") in args.profile]

    print(f"{args.condition} 条件下共 {len(targets)} 条记录，开始逐条检查...\n")

    malformed = []
    for r in targets:
        shown = r["result"]["shown"]
        report = analyze_shown(shown)
        if not report["overall_compliant"] or not report["parts_ok"]:
            malformed.append(
                {
                    "run_id": r.get("run_id"),
                    "profile_id": r.get("profile_id"),
                    "condition": r.get("condition"),
                    "divergence_check": r.get("result", {}).get("divergence_check"),
                    **report,
                }
            )

    print("=" * 70)
    print(f"发现 {len(malformed)} / {len(targets)} 条不合规记录")
    print("=" * 70)

    for m in malformed:
        print(f"\n--- {m['profile_id']} ({m['run_id']}) ---")
        print(
            f"  段数: {m['num_parts']} (期望 3)  |  整体合规: {m['overall_compliant']}"
        )
        for p in m["parts"]:
            flag = "OK" if p["compliant"] else "FAIL"
            print(
                f"  [part {p['part_index']}] [{flag}] "
                f"{p['word_count']} 词 / {p['char_count']} 字符  "
                f"(CAUSE={p['has_cause']} PREDICTION={p['has_prediction']} NEXT_STEP={p['has_next_step']})"
            )
            preview = p["text"] if args.full_text else (p["text"] or "")[:200]
            print(f"      文本: {preview!r}")

    if args.save:
        with open(args.save, "w") as f:
            json.dump(malformed, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到 {args.save}")


if __name__ == "__main__":
    main()
