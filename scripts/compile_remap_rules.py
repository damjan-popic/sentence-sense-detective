#!/usr/bin/env python3
"""Compile and validate the versioned declarative English remap profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import ROOT

CONFIG_ROOT = ROOT / "config/remap/en"
DATA_ROOT = ROOT / "data/remap/en"
DEFAULT_PROFILE = CONFIG_ROOT / "profile.json"
DEFAULT_OUTPUT = DATA_ROOT / "compiled_rules.json"
DEFAULT_CASE_MATRIX = DATA_ROOT / "case_to_rule.json"
DEFAULT_MANUAL_GUARDS = DATA_ROOT / "manual_guards.jsonl"
DEFAULT_REPORT = ROOT / "reports/remap_contract_coverage.json"
DEFAULT_MARKDOWN = ROOT / "reports/remap_contract_coverage.md"

REQUIRED_RULE_FIELDS = {
    "rule_id",
    "version",
    "language",
    "layer",
    "dimension",
    "decision_class",
    "priority",
    "source_case_ids",
    "match",
    "target",
    "output",
    "action",
}
VALID_DIMENSIONS = {
    "word_class",
    "sentence_element",
    "clause_type",
    "clause_marker",
    "clause_structure",
    "clause_function",
    "quality_control",
}
VALID_DECISIONS = {"direct", "rule-based", "manual-review"}
VALID_ACTIONS = {"publish", "review", "reject"}
UNRESOLVED_COMMENTS = {
    "SE-SC-05": (
        "Martin's comment is only “#9”; its intended referent is not recoverable "
        "from the supplied extraction."
    ),
    "CL-MARK-01": (
        "Martin's comment says he does not understand source items #82–#92; "
        "the supplied extraction contains no more specific correction."
    ),
    "CL-STR-01": (
        "The comment “ditto @ #93-#102” points to an unresolved source-level "
        "comment rather than a formal terminology correction."
    ),
    "CL-FUNC-01": (
        "The comment “ditto @ #103-#108” points to an unresolved source-level "
        "comment rather than a formal terminology correction."
    ),
}


def read_json_yaml(path: Path) -> dict:
    """Read JSON-compatible YAML without adding a runtime YAML dependency."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: profiles must use JSON-compatible YAML: {error}") from error


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_rule(rule: dict, labels: dict[str, set[str]]) -> list[str]:
    errors = []
    missing = sorted(REQUIRED_RULE_FIELDS - set(rule))
    if missing:
        return [f"{rule.get('rule_id', '<missing>')}: missing {missing}"]
    rule_id = rule["rule_id"]
    if rule["language"] != "en":
        errors.append(f"{rule_id}: language must be en")
    if rule["layer"] not in VALID_DIMENSIONS or rule["dimension"] not in VALID_DIMENSIONS:
        errors.append(f"{rule_id}: invalid layer/dimension")
    if rule["layer"] != rule["dimension"]:
        errors.append(f"{rule_id}: layer and dimension must agree")
    if rule["decision_class"] not in VALID_DECISIONS:
        errors.append(f"{rule_id}: invalid decision class")
    if rule["action"] not in VALID_ACTIONS:
        errors.append(f"{rule_id}: invalid action")
    if (
        rule["action"] == "publish"
        and rule["decision_class"] == "manual-review"
    ):
        errors.append(f"{rule_id}: manual-review rule cannot publish")
    if not isinstance(rule["priority"], int) or rule["priority"] < 0:
        errors.append(f"{rule_id}: priority must be a non-negative integer")
    if not rule["source_case_ids"] or len(rule["source_case_ids"]) != len(
        set(rule["source_case_ids"])
    ):
        errors.append(f"{rule_id}: source case IDs must be non-empty and unique")
    target = rule.get("target", {})
    if target.get("strategy") not in {
        "anchor-token",
        "anchor-subtree",
        "clause-subtree",
        "predicate-complex",
        "coordinated-units",
        "discontinuous",
        "custom",
    }:
        errors.append(f"{rule_id}: invalid target strategy")
    output = rule.get("output", {})
    if output.get("label") not in labels.get(rule["dimension"], set()):
        errors.append(
            f"{rule_id}: {output.get('label')!r} is outside the controlled vocabulary"
        )
    if rule["action"] == "review" and not any(
        str(guard.get("reason") or "").strip()
        for guard in rule.get("guards", [])
    ):
        errors.append(f"{rule_id}: review rule must state a guard reason")
    if not str(rule.get("explanation_template") or "").strip():
        errors.append(f"{rule_id}: explanation template is required")
    anchor = rule.get("match", {}).get("anchor", {})
    if rule["dimension"] != "word_class":
        if not anchor.get("event_rule_id"):
            errors.append(f"{rule_id}: structural event rule ID is required")
        if anchor.get("event_status") not in {
            "auto-high-confidence",
            "needs-review",
        }:
            errors.append(f"{rule_id}: structural event status is invalid")
        if "event_label" in anchor:
            errors.append(
                f"{rule_id}: adapter pedagogical labels cannot drive matching"
            )
    return errors


def build_markdown(report: dict) -> str:
    lines = [
        "# Formal remap contract coverage",
        "",
        f"- Profile: `{report['profile_id']}`",
        f"- Source workbook SHA-256: `{report['source_workbook_sha256']}`",
        f"- Formal rules: {report['formal_rule_count']}",
        f"- Contract-backed rules: {report['contract_backed_rule_count']}",
        f"- Provisional POS rules: {report['provisional_pos_rule_count']}",
        f"- Contract cases: {report['case_count']}",
        f"- Covered publishable: {report['status_counts'].get('covered_publishable', 0)}",
        f"- Covered manual guard: {report['status_counts'].get('covered_manual_guard', 0)}",
        f"- Parser mismatch: {report['status_counts'].get('parser_mismatch', 0)}",
        (
            "- Unresolved teacher comments: "
            f"{report['status_counts'].get('unresolved_teacher_comment', 0)}"
        ),
        "",
        "## Cases",
        "",
        "| Case | Expected decision | Status | Rule IDs | Teacher-comment disposition |",
        "|---|---|---|---|---|",
    ]
    for row in report["cases"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["case_id"],
                    row["expected_decision"],
                    row["formalization_status"],
                    ", ".join(f"`{item}`" for item in row["rule_ids"]),
                    row["teacher_comment_disposition"].replace("|", "\\|"),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def compile_profile(profile_path: Path = DEFAULT_PROFILE) -> tuple[dict, dict, dict]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    contract_path = ROOT / profile["source_contract"]
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    seed = json.loads((DATA_ROOT / "case_to_rule_seed.json").read_text(encoding="utf-8"))
    tagset = json.loads(
        (ROOT / "config/pedagogical_tagset_en.json").read_text(encoding="utf-8")
    )
    labels = {
        dimension: set(details["labels"])
        for dimension, details in tagset["dimensions"].items()
    }
    rules = []
    source_files = []
    for name in profile["rule_files"]:
        path = profile_path.parent / name
        payload = path.read_bytes()
        source_files.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
        rules.extend(read_json_yaml(path).get("rules", []))
    lexical_path = profile_path.parent / profile["lexical_sets"]
    lexical_payload = lexical_path.read_bytes()
    lexical_sets = read_json_yaml(lexical_path)
    source_files.append(
        {
            "path": str(lexical_path.relative_to(ROOT)),
            "bytes": len(lexical_payload),
            "sha256": sha256_bytes(lexical_payload),
        }
    )
    errors = []
    for rule in rules:
        errors.extend(validate_rule(rule, labels))
    rule_ids = [rule.get("rule_id") for rule in rules]
    duplicates = sorted(
        rule_id for rule_id, count in Counter(rule_ids).items() if count > 1
    )
    if duplicates:
        errors.append(f"duplicate formal rule IDs: {duplicates}")
    event_signatures = [
        (
            rule["rule_id"],
            (
                rule.get("match", {}).get("anchor", {}).get("event_rule_id"),
                rule.get("match", {}).get("anchor", {}).get("event_status"),
                rule.get("match", {}).get("anchor", {}).get(
                    "event_review_reason"
                ),
                rule.get("match", {}).get("anchor", {}).get("event_variant"),
            ),
        )
        for rule in rules
        if rule["dimension"] != "word_class"
    ]
    signature_counts = Counter(signature for _, signature in event_signatures)
    for rule_id, signature in event_signatures:
        if signature_counts[signature] > 1:
            errors.append(
                f"{rule_id}: structural event signature is not unique: "
                f"{signature}"
            )
    contract_cases = contract.get("cases", [])
    contract_by_id = {case["case_id"]: case for case in contract_cases}
    seed_ids = [row["case_id"] for row in seed.get("rows", [])]
    if len(contract_cases) != 106 or len(contract_by_id) != 106:
        errors.append("the formal contract must contain 106 unique cases")
    if seed_ids != [case["case_id"] for case in contract_cases]:
        errors.append("case-to-rule seed differs from the contract")
    expected_decisions = Counter(
        case["reference"]["expected_decision"] for case in contract_cases
    )
    if expected_decisions != Counter(
        {"OK": 26, "Rule-based OK": 60, "Needs manual review": 20}
    ):
        errors.append(f"unexpected contract decision counts: {dict(expected_decisions)}")
    if (
        contract.get("metadata", {}).get("source_sha256")
        != profile["source_workbook_sha256"]
    ):
        errors.append("profile and contract workbook hashes differ")
    case_rules = defaultdict(list)
    for rule in rules:
        for case_id in rule["source_case_ids"]:
            if case_id == "POS-PROFILE-EN-1.0.0":
                continue
            if case_id not in contract_by_id:
                errors.append(f"{rule['rule_id']}: unknown source case {case_id}")
            else:
                case_rules[case_id].append(rule)
    missing_cases = sorted(set(contract_by_id) - set(case_rules))
    if missing_cases:
        errors.append(f"contract cases without a formal rule: {missing_cases}")
    for case_id, case in contract_by_id.items():
        if case["reference"]["expected_decision"] == "Needs manual review" and any(
            rule["action"] == "publish" for rule in case_rules.get(case_id, [])
        ):
            errors.append(f"{case_id}: manual-review case has a publishing rule")
    if errors:
        raise ValueError("\n".join(errors))

    normalized_rules = sorted(rules, key=lambda item: item["rule_id"])
    compiled_core = {
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "language": "en",
        "source_contract_sha256": sha256_bytes(contract_path.read_bytes()),
        "source_workbook_sha256": profile["source_workbook_sha256"],
        "source_files": sorted(source_files, key=lambda item: item["path"]),
        "lexical_sets": lexical_sets["sets"],
        "rules": normalized_rules,
    }
    profile_sha256 = sha256_bytes(canonical_bytes(compiled_core))
    compiled = {
        **compiled_core,
        "profile_sha256": profile_sha256,
    }
    matrix_rows = []
    for seed_row in seed["rows"]:
        case_id = seed_row["case_id"]
        case = contract_by_id[case_id]
        mapped = sorted(case_rules[case_id], key=lambda item: item["rule_id"])
        expected = case["reference"]["expected_decision"]
        if case_id in UNRESOLVED_COMMENTS:
            status = "unresolved_teacher_comment"
            disposition = UNRESOLVED_COMMENTS[case_id]
        elif expected == "Needs manual review":
            status = "covered_manual_guard"
            disposition = "Implemented as an explicit review guard."
        else:
            status = "covered_publishable"
            disposition = (
                "Implemented in the rule output, structural condition, exclusion, "
                "or dimension separation."
            )
        matrix_rows.append(
            {
                **seed_row,
                "rule_ids": [rule["rule_id"] for rule in mapped],
                "formalization_status": status,
                "teacher_comment": case.get("martin_comment"),
                "teacher_comment_disposition": disposition,
            }
        )
    matrix = {
        "profile_id": profile["profile_id"],
        "profile_sha256": profile_sha256,
        "contract_version": contract["metadata"]["contract_version"],
        "rows": matrix_rows,
    }
    report_cases = [
        {
            "case_id": row["case_id"],
            "expected_decision": row["expected_decision"],
            "correct_mapping": row["correct_mapping"],
            "formalization_status": row["formalization_status"],
            "rule_ids": row["rule_ids"],
            "teacher_comment": row["teacher_comment"],
            "teacher_comment_disposition": row["teacher_comment_disposition"],
        }
        for row in matrix_rows
    ]
    report = {
        "profile_id": profile["profile_id"],
        "profile_sha256": profile_sha256,
        "source_workbook_sha256": profile["source_workbook_sha256"],
        "formal_rule_count": len(rules),
        "contract_backed_rule_count": sum(
            "POS-PROFILE-EN-1.0.0" not in rule["source_case_ids"]
            for rule in rules
        ),
        "provisional_pos_rule_count": sum(
            rule["dimension"] == "word_class" for rule in rules
        ),
        "rule_counts_by_dimension": dict(
            sorted(Counter(rule["dimension"] for rule in rules).items())
        ),
        "rule_counts_by_action": dict(
            sorted(Counter(rule["action"] for rule in rules).items())
        ),
        "rule_counts_by_decision_class": dict(
            sorted(Counter(rule["decision_class"] for rule in rules).items())
        ),
        "case_count": len(matrix_rows),
        "expected_decision_counts": dict(sorted(expected_decisions.items())),
        "status_counts": dict(
            sorted(Counter(row["formalization_status"] for row in matrix_rows).items())
        ),
        "cases": report_cases,
    }
    return compiled, matrix, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-matrix", type=Path, default=DEFAULT_CASE_MATRIX)
    parser.add_argument(
        "--manual-guards", type=Path, default=DEFAULT_MANUAL_GUARDS
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        compiled, matrix, report = compile_profile(args.profile)
        for path, value in (
            (args.output, compiled),
            (args.case_matrix, matrix),
            (args.report, report),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8")
                + b"\n"
            )
        args.manual_guards.parent.mkdir(parents=True, exist_ok=True)
        with args.manual_guards.open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            for rule in compiled["rules"]:
                if rule["action"] != "review":
                    continue
                handle.write(
                    json.dumps(
                        {
                            "profile_id": compiled["profile_id"],
                            "profile_sha256": compiled["profile_sha256"],
                            "rule_id": rule["rule_id"],
                            "dimension": rule["dimension"],
                            "decision_class": rule["decision_class"],
                            "source_case_ids": rule["source_case_ids"],
                            "match": rule["match"],
                            "guards": rule["guards"],
                            "output": rule["output"],
                            "action": rule["action"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(build_markdown(report), encoding="utf-8")
        print(
            f"Compiled {report['formal_rule_count']} formal rules with "
            f"{report['case_count']}/106 contract coverage "
            f"(profile {report['profile_sha256']})."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Formal remap compilation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
