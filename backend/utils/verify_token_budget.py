import argparse
import json
import sys
from pathlib import Path

import numpy as np

MAX_TOKENS_CAP = 300  # run_simulation.py 里 TokenTracker(max_tokens=300)


def load_results(path: str) -> list[dict]:
    results = []
    with open(path) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def word_count(text: str) -> int:
    return len((text or "").split())


def check_format(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "CAUSE" in t and "PREDICTION" in t and "NEXT STEP" in t


def is_compliant(shown) -> bool:
    parts = shown if isinstance(shown, list) else [shown]
    return len(parts) > 0 and all(check_format(p) for p in parts)


def get_summarizer_call(record: dict) -> dict | None:
    """summarizer 永远是 diagnosis_calls 列表里的最后一次调用。"""
    calls = record.get("token_usage", {}).get("diagnosis_calls", [])
    if not calls:
        return None
    return calls[-1]


def main():
    parser = argparse.ArgumentParser(description="验证 competing 条件的 token 预算假设")
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--near-cap-threshold",
        type=int,
        default=20,
        help="output_tokens 距离 300 的差值在这个范围内，算作'贴着预算上限'（默认20）",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: 找不到文件 {args.input}")
        sys.exit(1)

    results = load_results(args.input)
    competing = [
        r
        for r in results
        if r.get("condition") == "competing" and r.get("result", {}).get("shown")
    ]
    print(f"competing 条件共 {len(competing)} 条有效记录\n")

    compliant_tokens = []
    malformed_tokens = []
    missing_call_info = []

    rows = []
    for r in competing:
        shown = r["result"]["shown"]
        compliant = is_compliant(shown)
        num_parts = len(shown) if isinstance(shown, list) else 1
        call = get_summarizer_call(r)
        if call is None:
            missing_call_info.append(r.get("profile_id"))
            continue
        out_tok = call["output_tokens"]
        near_cap = (MAX_TOKENS_CAP - out_tok) <= args.near_cap_threshold
        rows.append(
            {
                "profile_id": r.get("profile_id"),
                "compliant": compliant,
                "num_parts": num_parts,
                "summarizer_output_tokens": out_tok,
                "near_cap": near_cap,
            }
        )
        if compliant and num_parts == 3:
            compliant_tokens.append(out_tok)
        else:
            malformed_tokens.append(out_tok)

    print("=" * 70)
    print("逐条明细（按 output_tokens 从高到低排序）")
    print("=" * 70)
    for row in sorted(rows, key=lambda x: -x["summarizer_output_tokens"]):
        flag = "MALFORMED" if not (row["compliant"] and row["num_parts"] == 3) else "OK"
        cap_flag = " <-- 贴着预算上限" if row["near_cap"] else ""
        print(
            f"  {row['profile_id']:8s} [{flag:9s}] "
            f"parts={row['num_parts']}  "
            f"summarizer_output_tokens={row['summarizer_output_tokens']:4d}/{MAX_TOKENS_CAP}"
            f"{cap_flag}"
        )

    print("\n" + "=" * 70)
    print("汇总对比")
    print("=" * 70)
    if compliant_tokens:
        arr = np.array(compliant_tokens)
        print(
            f"  合规记录 (n={len(arr)}): "
            f"mean={arr.mean():.1f}, max={arr.max()}, "
            f">=280 token 的比例: {(arr >= 280).sum()}/{len(arr)}"
        )
    if malformed_tokens:
        arr = np.array(malformed_tokens)
        print(
            f"  不合规记录 (n={len(arr)}): "
            f"mean={arr.mean():.1f}, max={arr.max()}, "
            f">=280 token 的比例: {(arr >= 280).sum()}/{len(arr)}"
        )

    if missing_call_info:
        print(
            f"\n注意: {len(missing_call_info)} 条记录没有 token_usage 信息，"
            f"已跳过: {missing_call_info}"
        )

    print("\n" + "=" * 70)
    print("结论判定")
    print("=" * 70)
    if compliant_tokens and malformed_tokens:
        c_arr, m_arr = np.array(compliant_tokens), np.array(malformed_tokens)
        c_near_cap_pct = (
            100 * (c_arr >= MAX_TOKENS_CAP - args.near_cap_threshold).sum() / len(c_arr)
        )
        m_near_cap_pct = (
            100 * (m_arr >= MAX_TOKENS_CAP - args.near_cap_threshold).sum() / len(m_arr)
        )
        print(
            f"  合规记录贴着预算上限的比例: {c_near_cap_pct:.0f}%\n"
            f"  不合规记录贴着预算上限的比例: {m_near_cap_pct:.0f}%"
        )
        if m_near_cap_pct > c_near_cap_pct + 20:
            print(
                "\n  => 支持假设：不合规记录明显更容易撞到 output_tokens 上限，"
                "说明 max_tokens=300 确实是截断的直接原因。"
            )
        else:
            print(
                "\n  => 不支持假设：不合规记录并没有显著更贴近 300 token 上限，"
                "截断可能不是（唯一）原因，需要另找解释"
                "（比如模型主动选择只写2段、或 prompt 本身歧义）。"
            )
    else:
        print("  数据不足以下结论（合规或不合规样本数为0）。")


if __name__ == "__main__":
    main()
