import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from scripts.run_simulation import (
    TokenTracker,
    run_single,
    PROFILES_PATH,
    RESULTS_DIR,
    MODEL_MAP,
)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def word_count(text: str) -> int:
    return len((text or "").split())


def check_format(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "CAUSE" in t and "PREDICTION" in t and "NEXT STEP" in t


def is_malformed(record: dict) -> bool:
    """与之前 analyze_simulation.py / inspect_malformed.py 保持一致的判定：
    段数不是3，或任意一段格式不合规，都算 malformed。"""
    if record.get("condition") != "competing":
        return False
    shown = record.get("result", {}).get("shown")
    if not shown:
        return False
    parts = shown if isinstance(shown, list) else [shown]
    if len(parts) != 3:
        return True
    return not all(check_format(p) for p in parts)


async def main():
    parser = argparse.ArgumentParser(
        description="定向重跑 competing 条件下因 token 截断而格式不合规的记录"
    )
    parser.add_argument(
        "--input", required=True, help="原始 run_simulation.py 输出的 .jsonl 路径"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=600,
        help="重跑时使用的 max_tokens（默认 600，原始跑批是 300）",
    )
    parser.add_argument("--concurrency", type=int, default=5, help="重跑时的最大并发数")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印会重跑哪些 profile，不实际调用 API",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: 找不到文件 {input_path}")
        sys.exit(1)

    original_records = load_jsonl(input_path)
    print(f"原始文件共 {len(original_records)} 条记录")

    malformed = [r for r in original_records if is_malformed(r)]
    malformed_profile_ids = {r["profile_id"] for r in malformed}
    print(
        f"发现 {len(malformed)} 条 competing 条件下格式不合规的记录，"
        f"涉及 {len(malformed_profile_ids)} 个 profile:"
    )
    print(f"  {sorted(malformed_profile_ids)}")

    if not malformed:
        print("没有需要重跑的记录，退出。")
        return

    if args.dry_run:
        print("\n--dry-run 模式，不实际调用 API。")
        return

    if not PROFILES_PATH.exists():
        print(f"ERROR: 找不到 profiles 文件 {PROFILES_PATH}")
        sys.exit(1)
    with open(PROFILES_PATH) as f:
        all_profiles = json.load(f)
    profiles_by_id = {p["id"]: p for p in all_profiles}

    target_profiles = []
    for pid in malformed_profile_ids:
        if pid not in profiles_by_id:
            print(f"  警告: profile {pid} 在 profiles.json 里找不到，跳过")
            continue
        target_profiles.append(profiles_by_id[pid])

    print(
        f"\n开始重跑 {len(target_profiles)} 个 profile "
        f"(condition=competing, max_tokens={args.max_tokens}, "
        f"concurrency={args.concurrency})..."
    )

    model = MODEL_MAP["opus"]
    tracker = TokenTracker(model=model, max_tokens=args.max_tokens)
    semaphore = asyncio.Semaphore(args.concurrency)

    tasks = []
    for profile in target_profiles:
        run_id = f"across_{profile['id']}_competing_rerun"
        tasks.append(
            run_single(profile, "competing", tracker, semaphore, run_id, "across")
        )

    overall_start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    rerun_records = []
    for r in results:
        if isinstance(r, Exception):
            rerun_records.append({"error": str(r), "test_type": "across"})
            print(f"  ERROR: {r}")
        else:
            rerun_records.append(r)
    elapsed = round(time.time() - overall_start, 1)

    # --- 保存本次重跑的原始记录 ---
    runs_dir = RESULTS_DIR / "runs"
    existing = sorted(runs_dir.glob("run*.jsonl"))
    if existing:
        last_num = int(existing[-1].name.split("_")[0].replace("run", ""))
        run_num = last_num + 1
    else:
        run_num = 1
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    rerun_file = runs_dir / f"run{run_num:03d}_{date_str}_opus_rerun_competing.jsonl"
    with open(rerun_file, "w") as f:
        for r in rerun_records:
            f.write(json.dumps(r) + "\n")
    print(f"\n重跑原始记录已保存到: {rerun_file}")

    # --- 检查重跑结果是否修复了格式问题 ---
    still_bad = [r for r in rerun_records if not isinstance(r, dict) or is_malformed(r)]
    fixed = [
        r
        for r in rerun_records
        if isinstance(r, dict) and r.get("result") and not is_malformed(r)
    ]
    print(f"重跑结果: {len(fixed)}/{len(rerun_records)} 修复成功")
    if still_bad:
        still_bad_ids = [r.get("profile_id", "unknown") for r in still_bad]
        print(f"  仍然不合规或出错: {still_bad_ids}")

    # --- 合并：用重跑结果替换原文件里对应 profile 的旧记录 ---
    rerun_by_profile = {
        r["profile_id"]: r
        for r in rerun_records
        if isinstance(r, dict) and r.get("profile_id")
    }
    merged = []
    for r in original_records:
        if (
            r.get("condition") == "competing"
            and r.get("profile_id") in rerun_by_profile
        ):
            merged.append(rerun_by_profile[r["profile_id"]])
        else:
            merged.append(r)

    fixed_file = input_path.parent / f"{input_path.stem}_fixed.jsonl"
    with open(fixed_file, "w") as f:
        for r in merged:
            f.write(json.dumps(r) + "\n")

    total_input = sum(
        r.get("total_input_tokens", 0) for r in rerun_records if isinstance(r, dict)
    )
    total_output = sum(
        r.get("total_output_tokens", 0) for r in rerun_records if isinstance(r, dict)
    )
    cost = (total_input / 1_000_000 * 15) + (total_output / 1_000_000 * 75)

    print(f"\n=== 完成 ===")
    print(f"耗时: {elapsed}s")
    print(f"本次重跑 token 消耗: {total_input:,} input + {total_output:,} output")
    print(f"预估成本: ${cost:.2f}")
    print(f"合并后的最终文件: {fixed_file}")
    print(f"\n下一步: python scripts/analyze_simulation.py --input {fixed_file}")


if __name__ == "__main__":
    asyncio.run(main())
