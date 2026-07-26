#!/usr/bin/env python3
"""Generate conservative deterministic pedagogical questions from Stanza output."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from pipeline_common import ROOT, read_json, read_jsonl, write_json, write_jsonl

DEFAULT_SENTENCES = ROOT / "data" / "corpus" / "sentences_10k.jsonl"
DEFAULT_ANNOTATIONS = ROOT / "data" / "corpus" / "sentences_10k.annotations.jsonl"
DEFAULT_TAGSET = ROOT / "config" / "pedagogical_tagset_en.json"
OUTPUT_ROOT = ROOT / "data" / "generated"
DEFAULT_CANDIDATES = OUTPUT_ROOT / "question_candidates.jsonl"
DEFAULT_ACCEPTED = OUTPUT_ROOT / "accepted_questions.jsonl"
DEFAULT_REJECTED = OUTPUT_ROOT / "rejected_questions.jsonl"
DEFAULT_PRIMARY = OUTPUT_ROOT / "sentence_primary_questions.json"
DEFAULT_REPORT = OUTPUT_ROOT / "generation_report.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "question_generation_report.md"

POS_BY_UPOS = {
    "PROPN": "Proper noun",
    "NOUN": "Noun",
    "PRON": "Pronoun",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "DET": "Determiner",
    "CCONJ": "Coordinator",
    "SCONJ": "Subordinator",
}
POS_EXPLANATIONS = {
    "Proper noun": "The highlighted word is an individual name, so it is a proper noun.",
    "Noun": "The highlighted word names a person, place, thing, or concept, so it is a noun.",
    "Pronoun": "The highlighted word stands in for a noun phrase, so it is a pronoun.",
    "Adjective": "The highlighted word describes a noun or completes an adjectival description.",
    "Adverb": "The highlighted word modifies an action, description, or circumstance.",
    "Determiner": "The highlighted word introduces or specifies a noun phrase.",
    "Lexical verb": "The highlighted word expresses the main action, event, or state.",
    "Auxiliary verb": "The highlighted word helps form the verb phrase.",
    "Modal auxiliary": "The highlighted word expresses meanings such as possibility, necessity, or prediction.",
    "Preposition": "The highlighted word heads a phrase expressing a relation such as place or direction.",
    "Particle": "The highlighted word combines with a verb as part of a multi-word verb.",
    "Subordinator": "The highlighted word introduces a subordinate clause.",
    "Coordinator": "The highlighted word joins units of equal grammatical status.",
    "Infinitival marker": "The highlighted “to” introduces an infinitive.",
}
SE_EXPLANATIONS = {
    "S — Subject": "The highlighted unit is the subject: it identifies who or what the clause is about.",
    "DO — Direct Object": "The highlighted unit is the direct object: it is directly affected by the verb.",
    "IO — Indirect Object": "The highlighted unit is the indirect object: it identifies the recipient or beneficiary.",
    "P — Predicator": "The highlighted verb functions as the predicator of the clause.",
    "SC — Subject Complement": "The highlighted unit completes the description or identification of the subject.",
    "A — Adverbial": "The highlighted unit adds circumstantial information to the clause.",
}
MARKER_RULES = {
    "because": "Subordinating conjunction",
    "although": "Subordinating conjunction",
    "though": "Subordinating conjunction",
    "if": "Subordinating conjunction",
    "unless": "Subordinating conjunction",
    "while": "Subordinating conjunction",
    "when": "Subordinating conjunction",
    "since": "Subordinating conjunction",
    "before": "Subordinating conjunction",
    "after": "Subordinating conjunction",
    "once": "Subordinating conjunction",
    "as": "Subordinating conjunction",
    "whether": "Interrogative subordinator",
}
CLAUSE_EXPLANATIONS = {
    "Complementizer": "The highlighted word introduces a clause that functions as a complement.",
    "Interrogative subordinator": "The highlighted word introduces an embedded question.",
    "Subordinating conjunction": "The highlighted word marks the clause as subordinate.",
    "Relative pronoun": "The highlighted word links the relative clause to the noun it modifies and has a role inside the clause.",
    "Relative adverb": "The highlighted word links the relative clause to the noun it modifies and expresses an adverbial relation.",
    "Infinitival marker": "The highlighted “to” introduces an infinitival clause.",
    "To-infinitival clause": "The highlighted clause is built around a to-infinitive.",
    "-ing clause": "The highlighted clause is built around an -ing verb form.",
    "Finite that-clause": "The highlighted clause is finite and is introduced by “that”.",
    "Nominal relative clause — function: S": (
        "The highlighted nominal relative clause functions as the subject "
        "of the larger clause."
    ),
    "Relative clause — function: PostM": "The highlighted relative clause modifies the noun that comes before it.",
    "Adverbial clause — function: A": "The highlighted clause functions as an adverbial in the larger sentence.",
}
FUSED_RELATIVE_HEAD_LEMMAS = {"what", "whatever", "whoever", "whichever"}
SUBJECT_RELATIONS = {"nsubj", "nsubj:outer"}


def stable_digest(*values: object) -> str:
    return hashlib.sha256(
        "\0".join(str(value) for value in values).encode("utf-8")
    ).hexdigest()


def classify_pos(word: dict, by_id: dict[int, dict]) -> tuple[str, str] | None:
    upos = word.get("upos")
    lemma = (word.get("lemma") or "").casefold()
    deprel = word.get("deprel") or ""
    if upos == "DET" and deprel not in {"det", "det:predet"}:
        # Stanza also uses DET for independent forms such as “all” and
        # fused-relative “what”. Their classroom treatment as determiner
        # versus pronoun is context-sensitive, so they are not safe POS items.
        return None
    if upos in POS_BY_UPOS:
        label = POS_BY_UPOS[upos]
        if label == "Proper noun" and not any(
            character.isupper() for character in (word.get("text") or "")
        ):
            return None
        return label, f"pos-{upos.casefold()}"
    if upos == "VERB":
        return "Lexical verb", "pos-lexical-verb"
    if upos == "AUX":
        if deprel not in {"aux", "aux:pass"}:
            # Copular and independent uses of be/have/do are not auxiliaries
            # in the pedagogical inventory used by this project.
            return None
        if word.get("xpos") == "MD":
            return "Modal auxiliary", "pos-modal-auxiliary"
        if lemma in {"be", "have", "do"}:
            return "Auxiliary verb", "pos-primary-auxiliary"
        return None
    if upos == "ADP":
        if deprel == "compound:prt":
            return "Particle", "pos-particle"
        return "Preposition", "pos-preposition"
    if upos == "PART":
        if deprel == "compound:prt":
            return "Particle", "pos-particle"
        if lemma == "to":
            head = by_id.get(word.get("head"))
            if head and head.get("upos") == "VERB":
                return "Infinitival marker", "pos-infinitival-marker"
    return None


def children_by_head(words: list[dict]) -> dict[int, list[dict]]:
    children = defaultdict(list)
    for word in words:
        children[word.get("head")].append(word)
    return children


def subtree(word_id: int, by_id: dict[int, dict], children: dict[int, list[dict]]) -> list[dict]:
    found = []
    stack = [word_id]
    while stack:
        current = stack.pop()
        word = by_id.get(current)
        if not word:
            continue
        found.append(word)
        stack.extend(child["id"] for child in children.get(current, []))
    return sorted(found, key=lambda word: word["id"])


def contiguous_span(words: list[dict]) -> dict | None:
    ordered = sorted(
        (
            word
            for word in words
            if isinstance(word.get("start_char"), int)
            and isinstance(word.get("end_char"), int)
        ),
        key=lambda word: (word["start_char"], word["end_char"]),
    )
    while ordered and ordered[0].get("upos") == "PUNCT":
        ordered.pop(0)
    while ordered and ordered[-1].get("upos") == "PUNCT":
        ordered.pop()
    if not ordered:
        return None
    return {
        "start": min(word["start_char"] for word in ordered),
        "end": max(word["end_char"] for word in ordered),
    }


def options_for(answer: str, dimension: str, tagset: dict, question_key: str) -> list[str]:
    labels = tagset["dimensions"][dimension]["labels"]
    if answer not in labels:
        raise ValueError(f"{answer!r} is outside controlled dimension {dimension}")
    distractors = sorted(
        (label for label in labels if label != answer),
        key=lambda label: stable_digest(question_key, label),
    )
    if len(distractors) < 3:
        raise ValueError(f"{dimension} does not provide three distractors")
    return [answer, *distractors[:3]]


def question(
    *,
    sentence: dict,
    dimension: str,
    target: dict,
    answer: str,
    prompt: str,
    explanation: str,
    confidence: float,
    rule_id: str,
    review_status: str,
    tagset: dict,
) -> dict:
    key = (
        f"{sentence['sentence_id']}:{dimension}:{target['start']}:{target['end']}:"
        f"{answer}:{rule_id}"
    )
    identifier = f"AUTO-{dimension.upper().replace('_', '-')}-{stable_digest(key)[:16]}"
    return {
        "question_id": identifier,
        "sentence_id": sentence["sentence_id"],
        "genre": sentence["source"]["genre"],
        "source_corpus": sentence["source"]["corpus"],
        "sentence": sentence["text"],
        "target_spans": [target],
        "mode": tagset["dimensions"][dimension]["mode"],
        "subskill": tagset["dimensions"][dimension]["subskill"],
        "dimension": dimension,
        "prompt": prompt,
        "answer": answer,
        "options": options_for(answer, dimension, tagset, key),
        "explanation": explanation,
        "difficulty": sentence["selection"]["difficulty"],
        "confidence": confidence,
        "rule_id": rule_id,
        "review_status": review_status,
    }


def pos_candidates(sentence: dict, words: list[dict], tagset: dict) -> list[dict]:
    by_id = {word["id"]: word for word in words}
    candidates = []
    for word in words:
        result = classify_pos(word, by_id)
        if not result:
            continue
        answer, rule_id = result
        target = {"start": word["start_char"], "end": word["end_char"]}
        candidates.append(
            question(
                sentence=sentence,
                dimension="word_class",
                target=target,
                answer=answer,
                prompt="Which part of speech is the highlighted word?",
                explanation=POS_EXPLANATIONS[answer],
                confidence=0.99 if word["upos"] in {"PROPN", "NOUN", "ADJ"} else 0.97,
                rule_id=rule_id,
                review_status="auto-high-confidence",
                tagset=tagset,
            )
        )
    basis = sentence["selection"]["primary_pos_candidate"]
    candidates.sort(
        key=lambda item: (
            0
            if item["target_spans"][0] == {
                "start": basis["start"],
                "end": basis["end"],
            }
            and item["answer"] == basis["label"]
            else 1,
            stable_digest(item["question_id"]),
        )
    )
    return candidates[:2]


def sentence_element_candidates(
    sentence: dict, words: list[dict], tagset: dict
) -> list[dict]:
    by_id = {word["id"]: word for word in words}
    children = children_by_head(words)
    high = []
    review = []
    for word in words:
        relation = word.get("deprel") or ""
        answer = rule_id = None
        confidence = 0.0
        status = "auto-high-confidence"
        if relation == "nsubj" and word.get("deprel") != "expl":
            answer, rule_id, confidence = "S — Subject", "se-nsubj-simple", 0.96
        elif relation == "obj":
            head = by_id.get(word.get("head"))
            if head and head.get("upos") == "VERB":
                answer, rule_id, confidence = "DO — Direct Object", "se-obj-active", 0.95
        elif relation == "iobj":
            answer, rule_id, confidence = "IO — Indirect Object", "se-iobj", 0.95
        elif relation == "root" and word.get("upos") == "VERB":
            verb_children = children.get(word["id"], [])
            if not any(
                child.get("deprel") in {"aux", "aux:pass", "compound:prt"}
                for child in verb_children
            ):
                answer, rule_id, confidence = "P — Predicator", "se-simple-predicator", 0.94
        elif relation == "root" and word.get("upos") in {"ADJ", "NOUN", "PROPN"}:
            if any(child.get("deprel") == "cop" for child in children.get(word["id"], [])):
                answer, rule_id, confidence = (
                    "SC — Subject Complement",
                    "se-copular-subject-complement",
                    0.95,
                )
        elif relation == "obl":
            answer, rule_id, confidence = "A — Adverbial", "se-obl-review", 0.60
            status = "needs-review"
        if not answer:
            continue
        target_words = subtree(word["id"], by_id, children)
        target = contiguous_span(target_words)
        if not target:
            continue
        candidate = question(
            sentence=sentence,
            dimension="sentence_element",
            target=target,
            answer=answer,
            prompt="What is the function of the highlighted word or phrase?",
            explanation=SE_EXPLANATIONS[answer],
            confidence=confidence,
            rule_id=rule_id,
            review_status=status,
            tagset=tagset,
        )
        (high if status == "auto-high-confidence" else review).append(candidate)
    high.sort(key=lambda item: (-item["confidence"], stable_digest(item["question_id"])))
    review.sort(key=lambda item: stable_digest(item["question_id"]))
    return high[:1] + (review[:1] if not high else [])


def relative_marker(word: dict, by_id: dict[int, dict]) -> str | None:
    lemma = (word.get("lemma") or "").casefold()
    head = by_id.get(word.get("head"))
    if not head or head.get("deprel") != "acl:relcl":
        return None
    if lemma in {"who", "whom", "whose", "which", "that"}:
        return "Relative pronoun"
    if lemma in {"where", "when", "why"}:
        return "Relative adverb"
    return None


def clause_candidates(sentence: dict, words: list[dict], tagset: dict) -> list[dict]:
    by_id = {word["id"]: word for word in words}
    children = children_by_head(words)
    candidates = []
    for word in words:
        lemma = (word.get("lemma") or "").casefold()
        answer = dimension = rule_id = None
        target_words = [word]
        if word.get("deprel") == "mark":
            head = by_id.get(word.get("head"))
            head_relation = (head or {}).get("deprel")
            if lemma == "that" and head_relation in {"ccomp", "xcomp", "acl"}:
                answer, rule_id = "Complementizer", "clause-marker-complementizer-that"
            elif lemma == "to" and head and head.get("xpos") == "VB":
                answer, rule_id = "Infinitival marker", "clause-marker-infinitival-to"
            elif lemma in MARKER_RULES:
                answer, rule_id = MARKER_RULES[lemma], f"clause-marker-{lemma}"
            dimension = "clause_marker"
        if not answer:
            relative = relative_marker(word, by_id)
            if relative:
                answer = relative
                dimension = "clause_marker"
                rule_id = f"clause-marker-{relative.casefold().replace(' ', '-')}"
        if answer:
            candidates.append(
                question(
                    sentence=sentence,
                    dimension=dimension,
                    target=contiguous_span(target_words),
                    answer=answer,
                    prompt="What type of clause marker is highlighted?",
                    explanation=CLAUSE_EXPLANATIONS[answer],
                    confidence=0.96,
                    rule_id=rule_id,
                    review_status="auto-high-confidence",
                    tagset=tagset,
                )
            )

    for word in words:
        relation = word.get("deprel") or ""
        clause_words = subtree(word["id"], by_id, children)
        target = contiguous_span(clause_words)
        if not target:
            continue
        marks = [
            child
            for child in children.get(word["id"], [])
            if child.get("deprel") == "mark"
        ]
        mark_lemmas = {(mark.get("lemma") or "").casefold() for mark in marks}
        answer = dimension = rule_id = None
        if relation == "acl:relcl":
            head = by_id.get(word.get("head"))
            head_lemma = ((head or {}).get("lemma") or "").casefold()
            if head_lemma in FUSED_RELATIVE_HEAD_LEMMAS:
                if (head or {}).get("deprel") not in SUBJECT_RELATIONS:
                    # Here the apparent relative-clause head is the wh-word,
                    # not a preceding noun. Only the reviewed subject label is
                    # safe to automate; other functions stay out of the bank.
                    continue
                nominal_words = [
                    item
                    for item in subtree(head["id"], by_id, children)
                    if item.get("upos") != "PUNCT"
                ]
                target = contiguous_span(nominal_words)
                answer = "Nominal relative clause — function: S"
                rule_id = "clause-type-nominal-relative-subject"
            else:
                answer = "Relative clause — function: PostM"
                rule_id = "clause-type-relative-postmodifier"
            dimension = "clause_type"
        elif relation == "advcl" and marks:
            answer = "Adverbial clause — function: A"
            dimension = "clause_type"
            rule_id = "clause-type-marked-adverbial"
        elif "to" in mark_lemmas and word.get("xpos") == "VB":
            answer = "To-infinitival clause"
            dimension = "clause_structure"
            rule_id = "clause-structure-to-infinitive"
        elif word.get("xpos") == "VBG" and relation in {"advcl", "acl", "xcomp", "ccomp"}:
            answer = "-ing clause"
            dimension = "clause_structure"
            rule_id = "clause-structure-ing"
        elif "that" in mark_lemmas and relation in {"ccomp", "acl"}:
            answer = "Finite that-clause"
            dimension = "clause_structure"
            rule_id = "clause-structure-finite-that"
        if answer:
            prompt = {
                "clause_type": "Which description best fits the highlighted clause?",
                "clause_structure": "What is the structure of the highlighted clause?",
            }[dimension]
            candidates.append(
                question(
                    sentence=sentence,
                    dimension=dimension,
                    target=target,
                    answer=answer,
                    prompt=prompt,
                    explanation=CLAUSE_EXPLANATIONS[answer],
                    confidence=0.93,
                    rule_id=rule_id,
                    review_status="auto-high-confidence",
                    tagset=tagset,
                )
            )
    candidates.sort(
        key=lambda item: (-item["confidence"], stable_digest(item["question_id"]))
    )
    return candidates[:1]


def validate_candidate(candidate: dict) -> str | None:
    options = candidate["options"]
    if len(options) != 4 or len(set(options)) != 4:
        return "options_not_four_unique"
    if candidate["answer"] not in options:
        return "answer_missing_from_options"
    sentence = candidate["sentence"]
    spans = candidate["target_spans"]
    if not spans:
        return "missing_target"
    for span in spans:
        if not (
            isinstance(span["start"], int)
            and isinstance(span["end"], int)
            and 0 <= span["start"] < span["end"] <= len(sentence)
        ):
            return "invalid_target_offsets"
    return None


def generate(sentences: list[dict], annotations: list[dict], tagset: dict):
    annotation_by_id = {record["sentence_id"]: record for record in annotations}
    candidates = []
    rejected = []
    primary = {}
    for index, sentence in enumerate(sentences, 1):
        annotation = annotation_by_id.get(sentence["sentence_id"])
        if not annotation or annotation["text"] != sentence["text"]:
            raise ValueError(f"{sentence['sentence_id']}: annotation text mismatch")
        words = annotation["tokens"]
        generated = [
            *pos_candidates(sentence, words, tagset),
            *sentence_element_candidates(sentence, words, tagset),
            *clause_candidates(sentence, words, tagset),
        ]
        accepted_for_sentence = []
        for candidate in generated:
            reason = validate_candidate(candidate)
            if reason:
                rejected.append({**candidate, "review_status": "rejected", "rejection_reason": reason})
            else:
                candidates.append(candidate)
                if candidate["review_status"] == "auto-high-confidence":
                    accepted_for_sentence.append(candidate)
        if not accepted_for_sentence:
            raise ValueError(
                f"{sentence['sentence_id']}: no accepted question survived generation"
            )
        primary[sentence["sentence_id"]] = accepted_for_sentence[0]["question_id"]
        if index % 1000 == 0:
            print(f"Generated candidates for {index}/{len(sentences)} sentences.", flush=True)
    candidates.sort(key=lambda item: item["question_id"])
    accepted = [
        candidate
        for candidate in candidates
        if candidate["review_status"] in {"auto-high-confidence", "human-reviewed"}
    ]
    rejected.sort(key=lambda item: item["question_id"])
    return candidates, accepted, rejected, primary


def build_report(
    sentences: list[dict],
    candidates: list[dict],
    accepted: list[dict],
    rejected: list[dict],
) -> dict:
    question_counts = Counter(candidate["sentence_id"] for candidate in accepted)
    grouped = Counter(
        "1" if count == 1 else "2" if count == 2 else "3+"
        for count in question_counts.values()
    )
    return {
        "sentence_count": len(sentences),
        "candidate_count": len(candidates),
        "accepted_count": len(accepted),
        "review_needed_count": sum(
            candidate["review_status"] == "needs-review" for candidate in candidates
        ),
        "rejected_count": len(rejected),
        "accepted_by_mode": dict(
            sorted(Counter(candidate["mode"] for candidate in accepted).items())
        ),
        "accepted_by_label": dict(
            sorted(Counter(candidate["answer"] for candidate in accepted).items())
        ),
        "candidate_status_counts": dict(
            sorted(Counter(candidate["review_status"] for candidate in candidates).items())
        ),
        "questions_per_sentence": {
            bucket: {
                "sentences": grouped[bucket],
                "percentage": round(grouped[bucket] / len(sentences) * 100, 2),
            }
            for bucket in ("1", "2", "3+")
        },
    }


def markdown_report(report: dict) -> str:
    lines = [
        "# Question-generation report",
        "",
        f"- Corpus sentences: {report['sentence_count']}",
        f"- Generated candidates: {report['candidate_count']}",
        f"- Accepted questions: {report['accepted_count']}",
        f"- Needs review: {report['review_needed_count']}",
        f"- Rejected questions: {report['rejected_count']}",
        "",
        "## Accepted questions by mode",
        "",
    ]
    for mode, count in report["accepted_by_mode"].items():
        lines.append(f"- {mode}: {count}")
    lines.extend(["", "## Accepted questions per sentence", ""])
    for bucket, values in report["questions_per_sentence"].items():
        lines.append(
            f"- {bucket}: {values['sentences']} ({values['percentage']}%)"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sentences", type=Path, default=DEFAULT_SENTENCES)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--tagset", type=Path, default=DEFAULT_TAGSET)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--accepted", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--rejected", type=Path, default=DEFAULT_REJECTED)
    parser.add_argument("--primary-index", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        sentences = list(read_jsonl(args.sentences))
        candidates, accepted, rejected, primary = generate(
            sentences,
            list(read_jsonl(args.annotations)),
            read_json(args.tagset),
        )
        write_jsonl(args.candidates, candidates)
        write_jsonl(args.accepted, accepted)
        write_jsonl(args.rejected, rejected)
        write_json(args.primary_index, primary)
        report = build_report(sentences, candidates, accepted, rejected)
        write_json(args.report, report)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_report(report), encoding="utf-8")
        print(
            f"Generated {len(candidates)} candidates: {len(accepted)} accepted, "
            f"{report['review_needed_count']} needing review, {len(rejected)} rejected."
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Question generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
