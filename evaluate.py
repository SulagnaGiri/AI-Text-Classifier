
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from classifier import MODEL, classify_message

BASE_DIR = Path(__file__).parent
TEST_FILE = BASE_DIR / "tests" / "test_cases.json"
RESULT_FILE = BASE_DIR / "evaluation_results.json"
REPORT_FILE = BASE_DIR / "EVALUATION.md"
FIELDS = ["request_type", "category", "subcategory", "affected_device", "priority"]
WORKERS = 3  # stays under the NVIDIA free tier limit of ~40 requests/minute


def run_case(test: dict) -> dict:
    start = time.time()
    record = {
        "id": test["id"],
        "type": test.get("type", "standard"),
        "message": test["message"],
        "expected": test["expected"],
    }
    try:
        actual = classify_message(test["message"])
    except Exception as error:
        record.update(error=str(error), all_correct=False, seconds=round(time.time() - start, 1))
        print(f"{test['id']}: ERROR - {error}")
        return record

    field_results = {
        field: {
            "expected": expected_value,
            "actual": actual.get(field),
            "correct": actual.get(field) == expected_value,
        }
        for field, expected_value in test["expected"].items()
    }
    all_correct = all(item["correct"] for item in field_results.values())
    record.update(
        actual=actual,
        field_results=field_results,
        all_correct=all_correct,
        seconds=round(time.time() - start, 1),
    )
    print(f"{test['id']}: {'PASS' if all_correct else 'FAIL'}")
    return record


def write_report(results: list) -> None:
    successful = [r for r in results if "actual" in r]
    field_correct = defaultdict(int)
    for r in successful:
        for field, item in r["field_results"].items():
            field_correct[field] += item["correct"]

    def case_accuracy(rows):
        return f"{sum(r['all_correct'] for r in rows)}/{len(rows)}" if rows else "0/0"

    standard = [r for r in successful if r["type"] == "standard"]
    edge = [r for r in successful if r["type"] == "edge_case"]
    errors = [r for r in results if "error" in r]

    lines = [
        "# Evaluation Results",
        "",
        f"Model: `{MODEL}` · Test cases: {len(results)} · Errors: {len(errors)}",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Fully correct cases | {case_accuracy(successful)} |",
        f"| Standard cases | {case_accuracy(standard)} |",
        f"| Edge cases | {case_accuracy(edge)} |",
    ]
    for field in FIELDS:
        if successful:
            lines.append(f"| `{field}` accuracy | {field_correct[field]}/{len(successful)} "
                         f"({field_correct[field] / len(successful):.0%}) |")

    lines += [
        "",
        "## Expected vs actual",
        "",
        "Mismatched fields are shown as **expected → actual**.",
        "",
        "| ID | Type | Message | Result | Mismatches | Confidence |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        message = r["message"].replace("|", "\\|")
        if "error" in r:
            lines.append(f"| {r['id']} | {r['type']} | {message} | ERROR | {r['error'][:80]} | |")
            continue
        mismatches = ", ".join(
            f"{field}: **{item['expected']} → {item['actual']}**"
            for field, item in r["field_results"].items() if not item["correct"]
        ) or "—"
        status = "✅ PASS" if r["all_correct"] else "❌ FAIL"
        lines.append(f"| {r['id']} | {r['type']} | {message} | {status} | {mismatches} | "
                     f"{r['actual'].get('confidence', '')} |")

    lines += ["", "Full JSON output for every case is in `evaluation_results.json`.", ""]
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    test_cases = json.loads(TEST_FILE.read_text(encoding="utf-8"))

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(run_case, test_cases))

    RESULT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(results)

    successful = [r for r in results if "actual" in r]
    passed = sum(r["all_correct"] for r in successful)
    print(f"\nEvaluation complete. Fully correct: {passed}/{len(results)}")
    print(f"Results: {RESULT_FILE.name}, report: {REPORT_FILE.name}")


if __name__ == "__main__":
    main()
