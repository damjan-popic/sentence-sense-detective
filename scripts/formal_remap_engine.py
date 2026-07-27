#!/usr/bin/env python3
"""Execute the compiled formal remap profile over pinned Stanza annotations."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pipeline_common import ROOT
from pedagogical_remapper import clause_specs as structural_clause_events
from pedagogical_remapper import (
    sentence_element_specs as structural_sentence_element_events,
)

DEFAULT_COMPILED_PROFILE = ROOT / "data/remap/en/compiled_rules.json"


def normalized_relation(word: dict) -> str:
    return word.get("deprel") or word.get("relation") or ""


def lemma(word: dict) -> str:
    return (word.get("lemma") or word.get("text") or "").casefold()


class FormalRemapEngine:
    """Apply declarative profile rules to structural graph-match events."""

    def __init__(self, profile_path: Path = DEFAULT_COMPILED_PROFILE):
        self.profile_path = profile_path
        self.profile = json.loads(profile_path.read_text(encoding="utf-8"))
        self.profile_id = self.profile["profile_id"]
        self.profile_sha256 = self.profile["profile_sha256"]
        self.rules = self.profile["rules"]
        self.pos_rules = sorted(
            (
                rule
                for rule in self.rules
                if rule["dimension"] == "word_class"
            ),
            key=lambda item: (-item["priority"], item["rule_id"]),
        )
        self.event_rules = defaultdict(list)
        for rule in self.rules:
            event_rule_id = rule.get("match", {}).get("anchor", {}).get(
                "event_rule_id"
            )
            if event_rule_id:
                self.event_rules[event_rule_id].append(rule)
        for rules in self.event_rules.values():
            rules.sort(key=lambda item: (-item["priority"], item["rule_id"]))

    @staticmethod
    def _token_matches(
        word: dict,
        by_id: dict[int, dict],
        conditions: dict,
    ) -> bool:
        scalar = {
            "upos": word.get("upos"),
            "xpos": word.get("xpos"),
            "deprel": normalized_relation(word),
            "lemma": lemma(word),
        }
        for field in ("upos", "xpos", "deprel", "lemma"):
            allowed = conditions.get(f"{field}_in")
            denied = conditions.get(f"{field}_not_in")
            if allowed is not None and scalar[field] not in allowed:
                return False
            if denied is not None and scalar[field] in denied:
                return False
        if conditions.get("text_has_upper") and not any(
            character.isupper() for character in (word.get("text") or "")
        ):
            return False
        head = by_id.get(word.get("head"))
        head_upos = conditions.get("head_upos_in")
        if head_upos is not None and (
            not head or head.get("upos") not in head_upos
        ):
            return False
        return True

    def word_class_specs(
        self,
        words: list[dict],
        annotation_metadata: dict,
    ) -> list[dict]:
        by_id = {word["id"]: word for word in words}
        results = []
        for word in words:
            matched = next(
                (
                    rule
                    for rule in self.pos_rules
                    if self._token_matches(
                        word,
                        by_id,
                        rule["match"].get("anchor", {}),
                    )
                ),
                None,
            )
            if not matched:
                continue
            results.append(
                self._formal_spec(
                    matched,
                    [{"start": word["start_char"], "end": word["end_char"]}],
                    words,
                    annotation_metadata,
                    ranking_confidence=(
                        0.99
                        if word.get("upos") in {"PROPN", "NOUN", "ADJ"}
                        else 0.97
                    ),
                    review_reason=None,
                    adapter_rule_id=None,
                )
            )
        return results

    @staticmethod
    def _event_matches(rule: dict, event: dict) -> bool:
        anchor = rule["match"]["anchor"]
        if (
            anchor.get("event_rule_id") != event.get("rule_id")
            or anchor.get("event_status") != event.get("review_status")
        ):
            return False
        required_reason = anchor.get("event_review_reason")
        required_variant = anchor.get("event_variant")
        return (
            (
                required_reason is None
                or required_reason == event.get("review_reason")
            )
            and (
                required_variant is None
                or required_variant == event.get("event_variant")
            )
        )

    def _formal_spec(
        self,
        rule: dict,
        target_spans: list[dict],
        words: list[dict],
        annotation_metadata: dict,
        *,
        ranking_confidence: float,
        review_reason: str | None,
        adapter_rule_id: str | None,
    ) -> dict:
        overlapping = [
            word
            for word in words
            if any(
                word.get("start_char", -1) < span["end"]
                and word.get("end_char", -1) > span["start"]
                for span in target_spans
            )
        ]
        action = rule["action"]
        guard_reason = next(
            (
                guard.get("reason")
                for guard in rule.get("guards", [])
                if guard.get("reason")
            ),
            None,
        )
        status = {
            "publish": "auto-high-confidence",
            "review": "needs-review",
            "reject": "rejected",
        }[action]
        return {
            "dimension": rule["dimension"],
            "answer": rule["output"]["label"],
            "target_spans": target_spans,
            "confidence": ranking_confidence,
            "rule_id": rule["rule_id"],
            "review_status": status,
            "review_reason": (
                guard_reason or review_reason
                if action != "publish"
                else None
            ),
            "reference_case_ids": rule["source_case_ids"],
            "explanation": rule["explanation_template"],
            "remap_profile": self.profile_id,
            "remap_profile_sha256": self.profile_sha256,
            "remap_rule_id": rule["rule_id"],
            "decision_class": rule["decision_class"],
            "action": action,
            "source_case_ids": rule["source_case_ids"],
            "matched_evidence": {
                "adapter_rule_id": adapter_rule_id,
                "target_strategy": rule["target"]["strategy"],
                "token_ids": [word["id"] for word in overlapping],
                "deprels": sorted(
                    {normalized_relation(word) for word in overlapping}
                ),
                "upos": sorted({word.get("upos") for word in overlapping}),
                "xpos": sorted(
                    {
                        word.get("xpos")
                        for word in overlapping
                        if word.get("xpos")
                    }
                ),
            },
            "stanza_version": annotation_metadata.get("stanza_version"),
            "model_bundle_sha256": annotation_metadata.get(
                "model_bundle_sha256"
            ),
        }

    def _apply_events(
        self,
        events: list[dict],
        words: list[dict],
        annotation_metadata: dict,
    ) -> list[dict]:
        formal = []
        for event in events:
            matched = next(
                (
                    rule
                    for rule in self.event_rules.get(event["rule_id"], [])
                    if self._event_matches(rule, event)
                ),
                None,
            )
            if not matched:
                raise ValueError(
                    "structural event has no compiled formal rule: "
                    f"{event['rule_id']} / {event['review_status']} / "
                    f"{event.get('event_variant') or '<default>'}"
                )
            formal.append(
                self._formal_spec(
                    matched,
                    event["target_spans"],
                    words,
                    annotation_metadata,
                    ranking_confidence=event["confidence"],
                    review_reason=event.get("review_reason"),
                    adapter_rule_id=event["rule_id"],
                )
            )
        return self._resolve_competing_matches(formal)

    @staticmethod
    def _resolve_competing_matches(specs: list[dict]) -> list[dict]:
        grouped = defaultdict(list)
        for item in specs:
            key = (
                item["dimension"],
                tuple(
                    (span["start"], span["end"])
                    for span in item["target_spans"]
                ),
            )
            grouped[key].append(item)
        resolved = []
        for matches in grouped.values():
            labels = {item["answer"] for item in matches}
            if len(labels) == 1:
                winner = sorted(
                    matches,
                    key=lambda item: (
                        item["action"] != "review",
                        item["rule_id"],
                    ),
                )[0]
                compatible = sorted(
                    {
                        item["rule_id"]
                        for item in matches
                        if item["rule_id"] != winner["rule_id"]
                    }
                )
                if compatible:
                    winner["matched_evidence"]["compatible_rule_ids"] = compatible
                resolved.append(winner)
                continue
            for item in matches:
                item["action"] = "review"
                item["review_status"] = "needs-review"
                item["review_reason"] = (
                    "Incompatible formal rules matched the same "
                    "sentence/dimension/target: "
                    + ", ".join(sorted(labels))
                )
                resolved.append(item)
        return sorted(
            resolved,
            key=lambda item: (
                item["dimension"],
                item["target_spans"][0]["start"],
                item["rule_id"],
            ),
        )

    def sentence_element_specs(
        self,
        words: list[dict],
        text: str,
        annotation_metadata: dict,
    ) -> list[dict]:
        return self._apply_events(
            structural_sentence_element_events(words, text),
            words,
            annotation_metadata,
        )

    def clause_specs(
        self,
        words: list[dict],
        text: str,
        annotation_metadata: dict,
    ) -> list[dict]:
        return self._apply_events(
            structural_clause_events(words, text),
            words,
            annotation_metadata,
        )
