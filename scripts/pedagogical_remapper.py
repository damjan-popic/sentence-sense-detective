#!/usr/bin/env python3
"""Map Stanza/UD evidence to the reviewed pedagogical grammar dimensions.

The rules in this module are deliberately asymmetric.  A technical relation is
evidence for a pedagogical analysis, not a classroom label in disguise.  Every
rule names the Martin-reviewed cases that justify it, and constructions whose
interpretation depends on lexical meaning or course policy remain visible in
the review queue.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

FINITE_XPOS = {"MD", "VBD", "VBP", "VBZ"}
CLAUSE_RELATIONS = {
    "root",
    "ccomp",
    "xcomp",
    "csubj",
    "advcl",
    "advcl:relcl",
    "acl",
    "acl:relcl",
    "conj",
}
SUBJECT_RELATIONS = {"nsubj", "nsubj:pass", "nsubj:outer", "csubj"}
FUSED_WH_LEMMAS = {
    "how",
    "what",
    "whatever",
    "wherever",
    "whoever",
    "whichever",
}
RELATIVE_PRONOUNS = {"who", "whom", "whose", "which", "that"}
RELATIVE_ADVERBS = {"where", "when", "why"}
CONTENT_OBJECT_VERBS = {
    "acknowledge",
    "admit",
    "agree",
    "announce",
    "answer",
    "argue",
    "assume",
    "believe",
    "claim",
    "confirm",
    "decide",
    "discover",
    "doubt",
    "expect",
    "explain",
    "feel",
    "find",
    "forget",
    "guess",
    "hear",
    "imagine",
    "indicate",
    "know",
    "learn",
    "mean",
    "mention",
    "notice",
    "observe",
    "promise",
    "prove",
    "realize",
    "remember",
    "report",
    "say",
    "see",
    "show",
    "state",
    "suggest",
    "suppose",
    "tell",
    "think",
    "understand",
    "wonder",
}
CONTENT_NOUNS = {
    "assumption",
    "belief",
    "claim",
    "decision",
    "doubt",
    "evidence",
    "fact",
    "fear",
    "hope",
    "idea",
    "news",
    "possibility",
    "promise",
    "proposal",
    "question",
    "report",
    "suggestion",
}
LINKING_VERBS = {
    "appear",
    "become",
    "feel",
    "get",
    "grow",
    "look",
    "prove",
    "remain",
    "seem",
    "smell",
    "sound",
    "stay",
    "taste",
    "turn",
}
PREDICATIVE_ROLE_NOUNS = {
    "advice",
    "aim",
    "ambition",
    "answer",
    "business",
    "duty",
    "goal",
    "hobby",
    "idea",
    "job",
    "plan",
    "problem",
    "purpose",
    "recommendation",
    "role",
    "task",
    "trouble",
}
COMPLEX_TRANSITIVE_VERBS = {
    "appoint",
    "call",
    "consider",
    "deem",
    "elect",
    "find",
    "keep",
    "leave",
    "make",
    "name",
    "paint",
    "prove",
    "render",
    "turn",
}
HIGH_CONFIDENCE_ING_OC_VERBS = {"catch", "find", "keep", "leave"}
PERCEPTION_VERBS = {"feel", "hear", "notice", "observe", "see", "watch"}
GERUND_COMPLEMENT_VERBS = {
    "avoid",
    "consider",
    "delay",
    "deny",
    "enjoy",
    "finish",
    "imagine",
    "keep",
    "mind",
    "miss",
    "practise",
    "practice",
    "recommend",
    "risk",
    "stop",
    "suggest",
}
DURATION_LEMMAS = {
    "century",
    "day",
    "decade",
    "hour",
    "minute",
    "month",
    "night",
    "second",
    "time",
    "week",
    "year",
}
TEMPORAL_ADVERBS = {
    "afterwards",
    "earlier",
    "first",
    "later",
    "now",
    "recently",
    "soon",
    "then",
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
}
NON_SENTENCE_ADVERBIALS = {
    "almost",
    "also",
    "even",
    "just",
    "more",
    "most",
    "n't",
    "nearly",
    "not",
    "only",
    "quite",
    "rather",
    "really",
    "so",
    "still",
    "too",
    "very",
}
PREPOSITIONAL_ING_MARKERS = {
    "after",
    "before",
    "by",
    "despite",
    "from",
    "in",
    "instead",
    "of",
    "on",
    "upon",
    "with",
    "without",
}
PREDICATIVE_ADV_COMPLEMENTS = {"off"}
TEMPORAL_RELATIVE_HOSTS = {"day", "date", "evening", "morning", "night", "time", "week"}


def _load_formal_lexical_sets() -> None:
    """Let the versioned profile govern lexical classes used by match adapters."""
    path = (
        Path(__file__).resolve().parents[1]
        / "config/remap/en/lexical_sets.yaml"
    )
    if not path.exists():
        return
    document = json.loads(path.read_text(encoding="utf-8"))
    configured = document.get("sets", {})
    names = (
        "FINITE_XPOS",
        "CLAUSE_RELATIONS",
        "SUBJECT_RELATIONS",
        "FUSED_WH_LEMMAS",
        "RELATIVE_PRONOUNS",
        "RELATIVE_ADVERBS",
        "CONTENT_OBJECT_VERBS",
        "CONTENT_NOUNS",
        "LINKING_VERBS",
        "PREDICATIVE_ROLE_NOUNS",
        "COMPLEX_TRANSITIVE_VERBS",
        "HIGH_CONFIDENCE_ING_OC_VERBS",
        "PERCEPTION_VERBS",
        "GERUND_COMPLEMENT_VERBS",
        "DURATION_LEMMAS",
        "TEMPORAL_ADVERBS",
        "NON_SENTENCE_ADVERBIALS",
        "PREPOSITIONAL_ING_MARKERS",
        "PREDICATIVE_ADV_COMPLEMENTS",
        "TEMPORAL_RELATIVE_HOSTS",
    )
    for name in names:
        key = name.casefold()
        values = configured.get(key)
        if not isinstance(values, list) or not values:
            raise ValueError(f"formal lexical set {key!r} is missing or empty")
        globals()[name] = set(values)


_load_formal_lexical_sets()


RULE_ANCHORS = {
    "se-subject-np": ["SE-S-01", "SE-S-02"],
    "se-subject-clause": ["SE-S-03", "SE-S-04", "SE-S-05"],
    "se-formal-postponed-subject": ["SE-S-06"],
    "se-predicator-simple": ["SE-P-01"],
    "se-operator-finite-auxiliary": ["SE-P-02"],
    "se-predicator-passive": ["SE-P-03"],
    "se-predicator-copula": ["SE-P-04"],
    "se-predicator-particle": ["SE-P-05"],
    "se-direct-object": ["SE-DO-01", "SE-DO-02", "SE-DO-03"],
    "se-clausal-direct-object": ["SE-DO-04", "SE-DO-05", "SE-DO-06"],
    "se-gerund-complement-review": ["SE-DO-07"],
    "se-indirect-object": ["SE-IO-01", "SE-IO-02", "SE-IO-03"],
    "se-subject-complement-copular": [
        "SE-SC-01",
        "SE-SC-02",
        "SE-SC-03",
        "SE-SC-04",
        "SE-SC-05",
        "SE-SC-06",
    ],
    "se-subject-complement-linking": ["SE-SC-07", "SE-SC-08"],
    "se-object-complement": ["SE-OC-01", "SE-OC-02", "SE-OC-05", "SE-OC-06"],
    "se-object-complement-pp-review": ["SE-OC-03"],
    "se-object-complement-bare-review": ["SE-OC-04"],
    "se-adverbial-direct": ["SE-A-01", "SE-A-02", "SE-A-04"],
    "se-adverbial-duration-review": ["SE-A-03"],
    "se-two-adverbials": ["SE-A-05"],
    "se-adverbial-clause": ["SE-A-06", "SE-A-07"],
    "se-ambiguous-pp-review": ["REVIEW-01"],
    "se-copular-temporal-review": ["REVIEW-02"],
    "clause-main": ["CL-MAIN-01"],
    "clause-main-complex-review": ["CL-MAIN-01"],
    "clause-nominal-do": ["CL-NOM-01", "CL-NOM-02", "CL-NOM-03"],
    "clause-nominal-relative-subject": ["CL-NOM-04"],
    "clause-dependent-question-subject": ["CL-NOM-05"],
    "clause-appositive": ["CL-NOM-06", "CL-NOM-07"],
    "clause-nominal-subject-complement": ["CL-NOM-08"],
    "clause-nominal-adjective-postmodifier": ["CL-NOM-09", "CL-NOM-10"],
    "clause-temporal-adverbial": ["CL-ADV-01"],
    "clause-causal-adverbial": ["CL-ADV-02", "CL-ADV-03"],
    "clause-conditional-adverbial": ["CL-ADV-04"],
    "clause-negative-conditional-adverbial": ["CL-ADV-05"],
    "clause-concessive-adverbial": ["CL-ADV-06"],
    "clause-purpose-adverbial": ["CL-ADV-07"],
    "clause-place-free-choice-adverbial": ["CL-ADV-08"],
    "clause-manner-comparison-adverbial": ["CL-ADV-09"],
    "clause-comparative-adjective-postmodifier": ["CL-ADV-10"],
    "clause-supplementive-review": ["CL-ADV-11"],
    "clause-generic-adverbial": ["CL-ADV-12", "CL-ADV-13", "CL-ADV-14", "CL-ADV-15"],
    "clause-relative-restrictive": ["CL-REL-01", "CL-REL-06", "CL-REL-08"],
    "clause-relative-zero-review": ["CL-REL-02", "CL-REL-07"],
    "clause-relative-generic": ["CL-REL-03", "CL-REL-04", "CL-REL-05"],
    "clause-relative-nonrestrictive": ["CL-REL-09"],
    "clause-relative-semantic-review": ["CL-REL-10"],
    "marker-complementizer": ["CL-MARK-01"],
    "marker-interrogative-whether": ["CL-MARK-02"],
    "marker-interrogative-if-review": ["CL-MARK-03"],
    "marker-subordinating-conjunction": ["CL-MARK-04", "CL-MARK-05", "CL-MARK-06"],
    "marker-relative-pronoun": ["CL-MARK-07"],
    "marker-relative-adverb": ["CL-MARK-08"],
    "marker-infinitival": ["CL-MARK-09"],
    "marker-preposition-ing": ["CL-STR-08"],
    "marker-zero-not-highlightable": ["CL-MARK-10"],
    "structure-finite-that": ["CL-STR-01"],
    "structure-finite-zero-that": ["CL-STR-02"],
    "structure-finite-wh": ["CL-STR-03"],
    "structure-finite-whether-if": ["CL-STR-04"],
    "structure-to-infinitive": ["CL-STR-05"],
    "structure-bare-infinitive-review": ["CL-STR-06"],
    "structure-ing": ["CL-STR-07"],
    "structure-preposition-ing": ["CL-STR-08"],
    "structure-reduced-review": ["CL-STR-09"],
    "structure-comparative-review": ["CL-STR-10"],
    "function-clause-subject": ["CL-FUNC-01"],
    "function-clause-direct-object": ["CL-FUNC-02"],
    "function-clause-subject-complement": ["CL-FUNC-03"],
    "function-clause-adverbial": ["CL-FUNC-04"],
    "function-clause-postmodifier": ["CL-FUNC-05"],
    "function-clause-object-complement-review": ["CL-FUNC-06"],
}


def lemma(word: dict | None) -> str:
    return ((word or {}).get("lemma") or (word or {}).get("text") or "").casefold()


def relation(word: dict | None) -> str:
    return (word or {}).get("deprel") or ""


def children_by_head(words: list[dict]) -> dict[int, list[dict]]:
    children: dict[int, list[dict]] = defaultdict(list)
    for word in words:
        children[word.get("head")].append(word)
    for values in children.values():
        values.sort(key=lambda item: item["id"])
    return children


def subtree_words(
    root_id: int,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
    *,
    excluded_relations: set[str] | None = None,
    excluded_ids: set[int] | None = None,
) -> list[dict]:
    excluded = excluded_relations or set()
    blocked_ids = excluded_ids or set()
    found = []
    stack = [root_id]
    while stack:
        current = stack.pop()
        word = by_id.get(current)
        if not word:
            continue
        found.append(word)
        for child in reversed(children.get(current, [])):
            if child["id"] in blocked_ids or relation(child) in excluded:
                continue
            stack.append(child["id"])
    return sorted(found, key=lambda item: item["id"])


def content_words(words: Iterable[dict]) -> list[dict]:
    return sorted(
        (
            word
            for word in words
            if word.get("upos") != "PUNCT"
            and isinstance(word.get("start_char"), int)
            and isinstance(word.get("end_char"), int)
        ),
        key=lambda item: (item["start_char"], item["end_char"]),
    )


def spans_from_words(words: Iterable[dict], text: str) -> list[dict]:
    ordered = content_words(words)
    if not ordered:
        return []
    spans = []
    start = ordered[0]["start_char"]
    end = ordered[0]["end_char"]
    for word in ordered[1:]:
        gap = text[end:word["start_char"]]
        if any(character.isalnum() for character in gap):
            spans.append({"start": start, "end": end})
            start = word["start_char"]
        end = word["end_char"]
    # Stanza may split the final full stop from an abbreviation such as
    # ``p.m.`` even though the final stop belongs to the highlighted phrase.
    if (
        str(ordered[-1].get("lemma") or "").endswith(".")
        and text[end:end + 1] == "."
    ):
        end += 1
    spans.append({"start": start, "end": end})
    return spans


def spec(
    *,
    dimension: str,
    answer: str,
    target_words: Iterable[dict],
    text: str,
    confidence: float,
    rule_id: str,
    review_status: str = "auto-high-confidence",
    review_reason: str | None = None,
    target_spans: list[dict] | None = None,
    event_variant: str | None = None,
) -> dict:
    if rule_id not in RULE_ANCHORS:
        raise KeyError(f"unanchored remapping rule {rule_id}")
    if review_status == "needs-review" and not review_reason:
        raise ValueError(f"{rule_id}: needs-review candidates require a reason")
    result = {
        "dimension": dimension,
        "answer": answer,
        "target_spans": (
            target_spans
            if target_spans is not None
            else spans_from_words(target_words, text)
        ),
        "confidence": confidence,
        "rule_id": rule_id,
        "review_status": review_status,
        "review_reason": review_reason,
        "reference_case_ids": RULE_ANCHORS[rule_id],
    }
    if event_variant:
        result["event_variant"] = event_variant
    return result


def deduplicate(specs: list[dict]) -> list[dict]:
    best: dict[tuple, dict] = {}
    for item in specs:
        key = (
            item["dimension"],
            item["answer"],
            tuple((span["start"], span["end"]) for span in item["target_spans"]),
        )
        previous = best.get(key)
        if previous is None or (
            previous["review_status"] == "needs-review"
            and item["review_status"] == "auto-high-confidence"
        ):
            best[key] = item
    return sorted(
        best.values(),
        key=lambda item: (
            item["dimension"],
            item["target_spans"][0]["start"] if item["target_spans"] else 10**9,
            item["rule_id"],
        ),
    )


def marker_words(
    head: dict,
    children: dict[int, list[dict]],
) -> list[dict]:
    markers = [
        child for child in children.get(head["id"], []) if relation(child) == "mark"
    ]
    expanded = list(markers)
    for marker in markers:
        expanded.extend(
            child
            for child in children.get(marker["id"], [])
            if relation(child) == "fixed"
        )
    return sorted({word["id"]: word for word in expanded}.values(), key=lambda item: item["id"])


def marker_phrase(head: dict, children: dict[int, list[dict]]) -> str:
    return " ".join(lemma(word) for word in marker_words(head, children))


def has_finite_verb(head: dict, children: dict[int, list[dict]]) -> bool:
    if head.get("xpos") in FINITE_XPOS:
        return True
    return any(
        child.get("xpos") in FINITE_XPOS
        and relation(child) in {"aux", "aux:pass", "cop"}
        for child in children.get(head["id"], [])
    )


def clause_words(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
    *,
    main: bool = False,
) -> list[dict]:
    excluded = {"parataxis"}
    excluded_ids: set[int] = set()
    if main:
        excluded |= {
            "advcl",
            "advcl:relcl",
            "ccomp",
            "acl",
            "acl:relcl",
        }
        excluded_ids = {
            child["id"]
            for child in children.get(head["id"], [])
            if lemma(child) in FUSED_WH_LEMMAS
            and any(
                relation(grandchild) in {"acl:relcl", "advcl:relcl"}
                for grandchild in children.get(child["id"], [])
            )
        }
        excluded_ids |= {
            child["id"]
            for child in children.get(head["id"], [])
            if relation(child) == "xcomp"
            and (
                child.get("upos") in {"VERB", "AUX"}
                or marker_words(child, children)
            )
        }
    elif relation(head) == "conj":
        excluded.add("cc")
    excluded_ids |= {
            child["id"]
            for child in children.get(head["id"], [])
            if relation(child) == "conj"
            and (
                marker_words(child, children)
                or any(
                    relation(grandchild) in {
                        "nsubj",
                        "nsubj:pass",
                        "nsubj:outer",
                        "csubj",
                    }
                    for grandchild in children.get(child["id"], [])
                )
            )
        }
    return subtree_words(
        head["id"],
        by_id,
        children,
        excluded_relations=excluded,
        excluded_ids=excluded_ids,
    )


def fused_relative_words(
    wh_word: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> list[dict]:
    return subtree_words(
        wh_word["id"], by_id, children, excluded_relations={"conj", "advcl"}
    )


def relative_clause_words(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> list[dict]:
    words = clause_words(head, by_id, children)
    antecedent = by_id.get(head.get("head"))
    if not antecedent:
        return words
    earliest = min((word["start_char"] for word in content_words(words)), default=10**9)
    for candidate in by_id.values():
        if (
            candidate["end_char"] <= earliest
            and candidate["start_char"] >= antecedent["end_char"]
            and (
                (candidate.get("xpos") or "").startswith("W")
                or lemma(candidate) in RELATIVE_PRONOUNS | RELATIVE_ADVERBS
            )
        ):
            words.append(candidate)
            words.extend(
                child
                for child in children.get(candidate["id"], [])
                if relation(child) == "case"
            )
    return sorted({word["id"]: word for word in words}.values(), key=lambda item: item["id"])


def subject_complement_words(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> list[dict]:
    return subtree_words(
        head["id"],
        by_id,
        children,
        excluded_relations={
            "nsubj",
            "nsubj:pass",
            "nsubj:outer",
            "csubj",
            "expl",
            "cop",
            "aux",
            "aux:pass",
            "advcl",
            "parataxis",
        },
    )


def predicative_clause_words(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> list[dict]:
    """Keep the subordinate clause intact while removing its outer copular frame."""
    markers = marker_words(head, children)
    marker_start = min(
        (marker["start_char"] for marker in markers),
        default=head["start_char"],
    )
    blocked = {
        child["id"]
        for child in children.get(head["id"], [])
        if relation(child) in {"nsubj:outer", "cop"}
        or (
            relation(child) == "aux"
            and child["end_char"] <= marker_start
        )
    }
    return subtree_words(
        head["id"],
        by_id,
        children,
        excluded_relations={"parataxis"},
        excluded_ids=blocked,
    )


def predicative_fused_relative_words(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> list[dict]:
    relatives = [
        child
        for child in children.get(head["id"], [])
        if relation(child) in {"acl:relcl", "advcl:relcl"}
    ]
    words = [head]
    for relative in relatives:
        words.extend(clause_words(relative, by_id, children))
    return sorted({word["id"]: word for word in words}.values(), key=lambda item: item["id"])


def is_predicative_gerund(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> bool:
    if head.get("xpos") != "VBG":
        return False
    be_aux = any(
        relation(child) == "aux" and lemma(child) == "be"
        for child in children.get(head["id"], [])
    )
    subjects = [
        child
        for child in children.get(head["id"], [])
        if relation(child) in {"nsubj", "nsubj:outer"}
    ]
    return bool(
        be_aux
        and subjects
        and any(lemma(subject) in PREDICATIVE_ROLE_NOUNS for subject in subjects)
    )


def sentence_element_specs(words: list[dict], text: str) -> list[dict]:
    by_id = {word["id"]: word for word in words}
    children = children_by_head(words)
    specs: list[dict] = []

    # Formal and postponed subjects remain review-visible as a linked analysis.
    for expletive in (word for word in words if relation(word) == "expl"):
        head = by_id.get(expletive.get("head"))
        postponed = next(
            (
                child
                for child in children.get((head or {}).get("id"), [])
                if relation(child) == "csubj"
            ),
            None,
        )
        if head and postponed:
            spans = (
                spans_from_words([expletive], text)
                + spans_from_words(clause_words(postponed, by_id, children), text)
            )
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="Formal S + Postponed S",
                    target_words=[],
                    target_spans=spans,
                    text=text,
                    confidence=0.62,
                    rule_id="se-formal-postponed-subject",
                    review_status="needs-review",
                    review_reason=(
                        "Formal it and the postponed clause must be confirmed as "
                        "two linked subject annotations."
                    ),
                )
            )

    # Subjects, including clausal subjects, use the full constituent span.
    for word in words:
        if relation(word) not in SUBJECT_RELATIONS:
            continue
        if relation(word).startswith("nsubj") and word.get("upos") == "PRON" and lemma(word) == "it":
            if any(relation(sibling) == "expl" for sibling in children.get(word.get("head"), [])):
                continue
        rule_id = (
            "se-subject-clause"
            if relation(word) == "csubj"
            or any(relation(child) == "acl:relcl" for child in children.get(word["id"], []))
            else "se-subject-np"
        )
        specs.append(
            spec(
                dimension="sentence_element",
                answer="S — Subject",
                target_words=subtree_words(word["id"], by_id, children),
                text=text,
                confidence=0.97,
                rule_id=rule_id,
            )
        )

    roots = [word for word in words if relation(word) == "root"]
    for root in roots:
        copulas = [child for child in children.get(root["id"], []) if relation(child) == "cop"]
        auxiliaries = [
            child
            for child in children.get(root["id"], [])
            if relation(child) in {"aux", "aux:pass"}
        ]
        particles = [
            child
            for child in children.get(root["id"], [])
            if relation(child) == "compound:prt"
        ]
        predicative_gerund = is_predicative_gerund(root, by_id, children)

        if copulas:
            for copula in copulas:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="P — Predicator",
                        target_words=[copula],
                        text=text,
                        confidence=0.97,
                        rule_id="se-predicator-copula",
                    )
                )
            outer_subject = any(
                relation(child) == "nsubj:outer"
                for child in children.get(root["id"], [])
            )
            sc_words = (
                predicative_clause_words(root, by_id, children)
                if outer_subject and marker_words(root, children)
                else subject_complement_words(root, by_id, children)
            )
            temporal = lemma(root) in DURATION_LEMMAS | TEMPORAL_ADVERBS
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="SC — Subject Complement",
                    target_words=sc_words,
                    text=text,
                    confidence=0.62 if temporal else 0.96,
                    rule_id=(
                        "se-copular-temporal-review"
                        if temporal
                        else "se-subject-complement-copular"
                    ),
                    review_status="needs-review" if temporal else "auto-high-confidence",
                    review_reason=(
                        "A temporal expression after copular be can be analysed "
                        "as SC or A; the reviewed framework requires confirmation."
                        if temporal
                        else None
                    ),
                )
            )
        elif predicative_gerund:
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="SC — Subject Complement",
                    target_words=subject_complement_words(root, by_id, children),
                    text=text,
                    confidence=0.94,
                    rule_id="se-subject-complement-copular",
                )
            )
        elif root.get("upos") == "VERB":
            finite_operators = [
                child
                for child in auxiliaries
                if relation(child) == "aux" and child.get("xpos") in FINITE_XPOS
            ]
            operator = min(finite_operators, key=lambda item: item["id"], default=None)
            if operator:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="Operator",
                        target_words=[operator],
                        text=text,
                        confidence=0.96,
                        rule_id="se-operator-finite-auxiliary",
                    )
                )
            p_words = [root, *particles]
            p_words.extend(
                auxiliary
                for auxiliary in auxiliaries
                if relation(auxiliary) == "aux:pass" or auxiliary is not operator
            )
            if any(relation(auxiliary) == "aux:pass" for auxiliary in auxiliaries):
                p_rule = "se-predicator-passive"
            elif particles:
                p_rule = "se-predicator-particle"
            else:
                p_rule = "se-predicator-simple"
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="P — Predicator",
                    target_words=p_words,
                    text=text,
                    confidence=0.95,
                    rule_id=p_rule,
                )
            )

        if lemma(root) in LINKING_VERBS and not any(
            relation(child) in {"obj", "iobj"}
            for child in children.get(root["id"], [])
        ):
            complements = [
                child
                for child in children.get(root["id"], [])
                if relation(child) == "xcomp"
                or (
                    relation(child) == "advmod"
                    and child["id"] > root["id"]
                    and lemma(child) in PREDICATIVE_ADV_COMPLEMENTS
                )
            ]
            for complement in complements:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="SC — Subject Complement",
                        target_words=subtree_words(complement["id"], by_id, children),
                        text=text,
                        confidence=0.92,
                        rule_id="se-subject-complement-linking",
                    )
                )

    # Objects and the complex-transitive guards.
    for head in words:
        head_children = children.get(head["id"], [])
        objects = [child for child in head_children if relation(child) == "obj"]
        indirects = [child for child in head_children if relation(child) == "iobj"]
        xcomps = [child for child in head_children if relation(child) == "xcomp"]
        matrix_lemma = lemma(head)
        benefactive_find_complements = [
            complement
            for complement in xcomps
            if complement.get("upos") in {"NOUN", "PROPN"}
            and any(
                relation(child) == "det" and lemma(child) in {"a", "an"}
                for child in children.get(complement["id"], [])
            )
        ]
        benefactive_find = (
            matrix_lemma == "find"
            and bool(benefactive_find_complements)
            and any(obj.get("upos") == "PRON" for obj in objects)
        )

        if benefactive_find:
            for obj in objects:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer=(
                            "IO — Indirect Object"
                            if obj.get("upos") == "PRON"
                            else "DO — Direct Object"
                        ),
                        target_words=subtree_words(obj["id"], by_id, children),
                        text=text,
                        confidence=0.90,
                        rule_id=(
                            "se-indirect-object"
                            if obj.get("upos") == "PRON"
                            else "se-direct-object"
                        ),
                    )
                )
            for complement in benefactive_find_complements:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="DO — Direct Object",
                        target_words=subtree_words(complement["id"], by_id, children),
                        text=text,
                        confidence=0.90,
                        rule_id="se-direct-object",
                    )
                )
        elif matrix_lemma == "consider" and objects and indirects:
            for indirect in indirects:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="DO — Direct Object",
                        target_words=subtree_words(indirect["id"], by_id, children),
                        text=text,
                        confidence=0.93,
                        rule_id="se-direct-object",
                    )
                )
            for obj in objects:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="OC — Object Complement",
                        target_words=subtree_words(obj["id"], by_id, children),
                        text=text,
                        confidence=0.92,
                        rule_id="se-object-complement",
                    )
                )
        else:
            for obj in objects:
                if obj.get("upos") in {"ADJ", "ADV"}:
                    continue
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="DO — Direct Object",
                        target_words=subtree_words(obj["id"], by_id, children),
                        text=text,
                        confidence=0.95,
                        rule_id="se-direct-object",
                    )
                )
            for indirect in indirects:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="IO — Indirect Object",
                        target_words=subtree_words(indirect["id"], by_id, children),
                        text=text,
                        confidence=0.95,
                        rule_id="se-indirect-object",
                    )
                )

        for complement in xcomps:
            if not objects:
                continue
            if benefactive_find and complement in benefactive_find_complements:
                continue
            if (
                complement.get("xpos") == "VBG"
                and matrix_lemma in HIGH_CONFIDENCE_ING_OC_VERBS
            ) or (
                complement.get("upos") in {"ADJ", "NOUN", "PROPN"}
                and matrix_lemma in COMPLEX_TRANSITIVE_VERBS
            ):
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="OC — Object Complement",
                        target_words=subtree_words(complement["id"], by_id, children),
                        text=text,
                        confidence=0.91,
                        rule_id="se-object-complement",
                    )
                )
            elif complement.get("xpos") == "VB" and matrix_lemma in PERCEPTION_VERBS:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="OC — Object Complement",
                        target_words=subtree_words(complement["id"], by_id, children),
                        text=text,
                        confidence=0.60,
                        rule_id="se-object-complement-bare-review",
                        review_status="needs-review",
                        review_reason=(
                            "Bare infinitives after perception verbs depend on the "
                            "course convention for OC versus clausal object."
                        ),
                    )
                )
            if (
                lemma(complement) in FUSED_WH_LEMMAS
                and any(relation(child) == "acl:relcl" for child in children.get(complement["id"], []))
                and matrix_lemma == "call"
            ):
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="OC — Object Complement",
                        target_words=fused_relative_words(complement, by_id, children),
                        text=text,
                        confidence=0.91,
                        rule_id="se-object-complement",
                    )
                )

        if objects and matrix_lemma in {"find", "leave", "keep"}:
            has_definite_object = any(
                any(
                    relation(child) == "det" and lemma(child) == "the"
                    for child in children.get(obj["id"], [])
                )
                for obj in objects
            )
            for oblique in (
                child
                for child in head_children
                if relation(child) in {"obl", "obl:unmarked"}
            ):
                is_reviewed_predicative_pp = (
                    matrix_lemma == "find" and has_definite_object
                )
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="OC — Object Complement",
                        target_words=subtree_words(oblique["id"], by_id, children),
                        text=text,
                        confidence=0.91 if is_reviewed_predicative_pp else 0.58,
                        rule_id="se-object-complement-pp-review",
                        review_status=(
                            "auto-high-confidence"
                            if is_reviewed_predicative_pp
                            else "needs-review"
                        ),
                        review_reason=(
                            None
                            if is_reviewed_predicative_pp
                            else (
                                "The PP may be predicated of the object, modify "
                                "the object noun phrase, or function as an adverbial."
                            )
                        ),
                    )
                )

    # Clausal objects and policy-controlled gerund complements.
    for clause in words:
        head = by_id.get(clause.get("head"))
        if relation(clause) == "ccomp" and head and head.get("upos") == "VERB":
            if lemma(head) == "tell":
                fused = next(
                    (
                        child
                        for child in children.get(clause["id"], [])
                        if lemma(child) in {"whoever", "whomever"}
                    ),
                    None,
                )
                if fused:
                    recipient_words = subtree_words(
                        clause["id"],
                        by_id,
                        children,
                        excluded_relations={"advcl", "conj"},
                    )
                    specs.append(
                        spec(
                            dimension="sentence_element",
                            answer="IO — Indirect Object",
                            target_words=recipient_words,
                            text=text,
                            confidence=0.90,
                            rule_id="se-indirect-object",
                        )
                    )
                    continue
            status = (
                "auto-high-confidence"
                if lemma(head) in CONTENT_OBJECT_VERBS
                else "needs-review"
            )
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="DO — Direct Object",
                    target_words=clause_words(clause, by_id, children),
                    text=text,
                    confidence=0.92 if status == "auto-high-confidence" else 0.59,
                    rule_id="se-clausal-direct-object",
                    review_status=status,
                    review_reason=(
                        None
                        if status == "auto-high-confidence"
                        else "The matrix verb does not license an automatic clausal-DO analysis."
                    ),
                )
            )
        elif (
            relation(clause) == "xcomp"
            and head
            and lemma(head) in GERUND_COMPLEMENT_VERBS
            and clause.get("xpos") == "VBG"
        ):
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="DO — Direct Object",
                    target_words=clause_words(clause, by_id, children),
                    text=text,
                    confidence=0.58,
                    rule_id="se-gerund-complement-review",
                    review_status="needs-review",
                    review_reason=(
                        "The teaching treatment of this -ing complement as DO "
                        "rather than a general clausal complement is policy-controlled."
                    ),
                )
            )

    # Adverbials and the PP-attachment/manual-review guard.
    for word in words:
        head = by_id.get(word.get("head"))
        rel = relation(word)
        if rel == "advmod" and head and head.get("upos") == "VERB":
            is_predicative_linking_complement = (
                lemma(head) in LINKING_VERBS
                and lemma(word) in PREDICATIVE_ADV_COMPLEMENTS
                and not any(
                    relation(child) in {"obj", "iobj"}
                    for child in children.get(head["id"], [])
                )
            )
            if (
                lemma(word) not in NON_SENTENCE_ADVERBIALS
                and not is_predicative_linking_complement
            ):
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="A — Adverbial",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.94,
                        rule_id="se-adverbial-direct",
                    )
                )
        elif rel in {"obl", "obl:unmarked"} and head:
            word_children = children.get(word["id"], [])
            case_lemmas = {lemma(child) for child in word_children if relation(child) == "case"}
            has_object_sibling = any(
                relation(sibling) in {"obj", "iobj"}
                for sibling in children.get(head["id"], [])
            )
            is_reviewed_predicative_oc = (
                lemma(head) == "find"
                and any(
                    relation(sibling) == "obj"
                    and any(
                        relation(child) == "det" and lemma(child) == "the"
                        for child in children.get(sibling["id"], [])
                    )
                    for sibling in children.get(head["id"], [])
                )
            )
            is_duration = lemma(word) in DURATION_LEMMAS
            is_clear_for_joy = lemma(word) == "joy" and "for" in case_lemmas
            is_temporal = lemma(word) in TEMPORAL_ADVERBS
            if is_reviewed_predicative_oc:
                continue
            if is_temporal:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="A — Adverbial",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.92,
                        rule_id="se-adverbial-direct",
                    )
                )
            elif has_object_sibling and not is_duration and not is_clear_for_joy:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="Context needed",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.45,
                        rule_id="se-ambiguous-pp-review",
                        review_status="needs-review",
                        review_reason=(
                            "PP attachment is ambiguous between event adverbial, "
                            "nominal modifier, and selected complement."
                        ),
                    )
                )
            elif is_duration:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="A — Adverbial",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.61,
                        rule_id="se-adverbial-duration-review",
                        review_status="needs-review",
                        review_reason=(
                            "Duration noun phrases receive variable technical "
                            "analyses and require confirmation as pedagogical A."
                        ),
                    )
                )
            elif is_clear_for_joy:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="A — Adverbial",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.92,
                        rule_id="se-adverbial-direct",
                    )
                )
            else:
                specs.append(
                    spec(
                        dimension="sentence_element",
                        answer="A — Adverbial",
                        target_words=subtree_words(word["id"], by_id, children),
                        text=text,
                        confidence=0.55,
                        rule_id="se-ambiguous-pp-review",
                        review_status="needs-review",
                        review_reason=(
                            "A technical oblique relation does not decide whether "
                            "the phrase is an adverbial or selected complement."
                        ),
                    )
                )
        elif rel == "advcl":
            phrase = marker_phrase(word, children)
            marked = bool(phrase)
            clear_unmarked = (
                word.get("xpos") == "VBG"
                and word["id"] == min(item["id"] for item in words)
                and lemma(word) in {"know", "knowing"}
            )
            status = "auto-high-confidence" if marked or clear_unmarked else "needs-review"
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="A — Adverbial",
                    target_words=clause_words(word, by_id, children),
                    text=text,
                    confidence=0.93 if status == "auto-high-confidence" else 0.60,
                    rule_id="se-adverbial-clause",
                    review_status=status,
                    review_reason=(
                        None
                        if status == "auto-high-confidence"
                        else "An unmarked non-finite supplementive clause requires semantic review."
                    ),
                )
            )

    # Reviewed two-adverbial pattern: directional home + purpose infinitive.
    for root in roots:
        directional = next(
            (
                child
                for child in children.get(root["id"], [])
                if relation(child) == "advmod" and lemma(child) == "home"
            ),
            None,
        )
        purpose = next(
            (
                child
                for child in children.get(root["id"], [])
                if relation(child) == "advcl"
                and marker_phrase(child, children) == "to"
            ),
            None,
        )
        if directional and purpose:
            specs.append(
                spec(
                    dimension="sentence_element",
                    answer="A + A — two Adverbials",
                    target_words=[],
                    target_spans=(
                        spans_from_words([directional], text)
                        + spans_from_words(clause_words(purpose, by_id, children), text)
                    ),
                    text=text,
                    confidence=0.91,
                    rule_id="se-two-adverbials",
                )
            )

    return deduplicate(specs)


def relative_marker_spec(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
    text: str,
) -> list[dict]:
    antecedent = by_id.get(head.get("head"))

    def belongs_to_relative_head(marker: dict) -> bool:
        if (
            antecedent
            and marker["id"] == antecedent["id"]
            and (
                (marker.get("xpos") or "").startswith("W")
                or lemma(marker) in RELATIVE_PRONOUNS | RELATIVE_ADVERBS
            )
        ):
            return True
        current = marker
        visited: set[int] = set()
        while current.get("head") and current["id"] not in visited:
            visited.add(current["id"])
            parent = by_id.get(current.get("head"))
            if not parent:
                return False
            if parent["id"] == head["id"]:
                return True
            if relation(parent) in CLAUSE_RELATIONS:
                return False
            current = parent
        return False

    clause = relative_clause_words(head, by_id, children)
    candidates = [
        word
        for word in clause
        if (
            (word.get("xpos") or "").startswith("W")
            or lemma(word) in RELATIVE_PRONOUNS | RELATIVE_ADVERBS
        )
        and belongs_to_relative_head(word)
    ]
    results = []
    for marker in candidates:
        if lemma(marker) in RELATIVE_PRONOUNS:
            answer, rule_id = "Relative pronoun", "marker-relative-pronoun"
        elif lemma(marker) in RELATIVE_ADVERBS:
            answer, rule_id = "Relative adverb", "marker-relative-adverb"
        else:
            continue
        results.append(
            spec(
                dimension="clause_marker",
                answer=answer,
                target_words=[marker],
                text=text,
                confidence=0.96,
                rule_id=rule_id,
            )
        )
    return results


def adverbial_type(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> tuple[str, str, str, float, str | None]:
    phrase = marker_phrase(head, children)
    root = next((word for word in by_id.values() if relation(word) == "root"), None)
    root_children = children.get((root or {}).get("id"), [])
    preceding_even = any(
        lemma(word) == "even"
        and word["end_char"] <= min(
            (marker["start_char"] for marker in marker_words(head, children)),
            default=head["start_char"],
        )
        for word in by_id.values()
    )
    if (
        not has_finite_verb(head, children)
        and (
            head.get("upos") in {"ADJ", "ADV"}
            or (head.get("xpos") == "VBG" and preceding_even)
        )
    ):
        return (
            "Adverbial clause — function: A",
            "clause-generic-adverbial",
            "needs-review",
            0.59,
            "The reduced clause lacks an overt finite verb and requires manual confirmation.",
        )
    if phrase == "because":
        return "Causal adverbial clause", "clause-causal-adverbial", "auto-high-confidence", 0.95, None
    if phrase == "since":
        causal_cue = any(
            child.get("xpos") == "MD" and lemma(child) in {"should", "must", "ought"}
            for child in root_children
        )
        if causal_cue:
            return "Causal adverbial clause", "clause-causal-adverbial", "auto-high-confidence", 0.91, None
        return (
            "Adverbial clause — function: A",
            "clause-generic-adverbial",
            "auto-high-confidence",
            0.92,
            None,
        )
    if phrase == "unless":
        return "Negative-conditional adverbial clause", "clause-negative-conditional-adverbial", "auto-high-confidence", 0.96, None
    if phrase == "if":
        return "Conditional adverbial clause", "clause-conditional-adverbial", "auto-high-confidence", 0.95, None
    if phrase in {"although", "though"}:
        return "Concessive adverbial clause", "clause-concessive-adverbial", "auto-high-confidence", 0.95, None
    if phrase == "while":
        head_copular = any(relation(child) == "cop" for child in children.get(head["id"], []))
        locative = head.get("upos") == "ADV" or lemma(head) in {"away", "out", "there"}
        contrast = any(lemma(child) in {"not", "n't"} for child in root_children)
        if head_copular and locative and not contrast:
            return "Temporal adverbial clause", "clause-temporal-adverbial", "auto-high-confidence", 0.92, None
        if contrast:
            return "Concessive adverbial clause", "clause-concessive-adverbial", "auto-high-confidence", 0.90, None
        return "Adverbial clause — function: A", "clause-generic-adverbial", "auto-high-confidence", 0.92, None
    if phrase in {"when", "before", "after", "once", "until", "whenever"}:
        return "Temporal adverbial clause", "clause-temporal-adverbial", "auto-high-confidence", 0.94, None
    if phrase in {"as if", "as though"}:
        return "Manner / comparison adverbial clause", "clause-manner-comparison-adverbial", "auto-high-confidence", 0.94, None
    if phrase == "so that":
        purpose_cue = any(
            child.get("xpos") == "MD" and lemma(child) in {"can", "could", "may", "might"}
            for child in children.get(head["id"], [])
        )
        if purpose_cue:
            return "Purpose adverbial clause", "clause-purpose-adverbial", "auto-high-confidence", 0.91, None
        return (
            "Purpose adverbial clause",
            "clause-purpose-adverbial",
            "needs-review",
            0.58,
            "So-that clauses require a semantic decision between purpose and result.",
        )
    if phrase == "to":
        return "Adverbial clause — function: A", "clause-generic-adverbial", "auto-high-confidence", 0.91, None
    if phrase in PREPOSITIONAL_ING_MARKERS and head.get("xpos") == "VBG":
        return "Adverbial clause — function: A", "clause-generic-adverbial", "auto-high-confidence", 0.91, None
    if not phrase and head.get("xpos") == "VBG":
        if head.get("start_char") == 0:
            return (
                "Supplementive non-finite clause — function: A",
                "clause-supplementive-review",
                "auto-high-confidence",
                0.91,
                None,
            )
        return (
            "Supplementive non-finite clause — function: A",
            "clause-supplementive-review",
            "needs-review",
            0.61,
            "The supplementive function is structurally plausible, but its semantic subtype requires review.",
        )
    return "Adverbial clause — function: A", "clause-generic-adverbial", "auto-high-confidence", 0.90, None


def comparative_pattern(
    head: dict,
    by_id: dict[int, dict],
    children: dict[int, list[dict]],
) -> bool:
    if marker_phrase(head, children) != "as":
        return False
    host = by_id.get(head.get("head"))
    if not host or host.get("upos") != "ADJ":
        return False
    return any(
        relation(child) == "advmod" and lemma(child) == "as"
        for child in children.get(host["id"], [])
    )


def clause_specs(words: list[dict], text: str) -> list[dict]:
    by_id = {word["id"]: word for word in words}
    children = children_by_head(words)
    specs: list[dict] = []
    roots = [word for word in words if relation(word) == "root"]

    # Main clause is a pedagogical type in its own right.
    for root in roots:
        imperative = "Mood=Imp" in str(root.get("feats") or "")
        overt_subject = any(
            relation(child) in SUBJECT_RELATIONS | {"expl"}
            for child in children.get(root["id"], [])
        )
        if not imperative and not (
            has_finite_verb(root, children) and overt_subject
        ):
            continue
        main_words = clause_words(root, by_id, children, main=True)
        main_spans = spans_from_words(main_words, text)
        complex_boundary = len(main_spans) != 1
        specs.append(
            spec(
                dimension="clause_type",
                answer="Main clause",
                target_words=main_words,
                text=text,
                confidence=0.98 if not complex_boundary else 0.58,
                rule_id=(
                    "clause-main"
                    if not complex_boundary
                    else "clause-main-complex-review"
                ),
                review_status=(
                    "auto-high-confidence"
                    if not complex_boundary
                    else "needs-review"
                ),
                review_reason=(
                    None
                    if not complex_boundary
                    else (
                        "Nested clause boundaries make the matrix clause "
                        "discontinuous; confirm the teaching highlight."
                    )
                ),
            )
        )

    # Fused/nominal relatives require reconstruction around the wh head.
    fused_heads = [
        word
        for word in words
        if lemma(word) in FUSED_WH_LEMMAS
        and any(
            relation(child) in {"acl:relcl", "advcl:relcl"}
            for child in children.get(word["id"], [])
        )
    ]
    fused_head_ids = {word["id"] for word in fused_heads}
    for fused in fused_heads:
        target = fused_relative_words(fused, by_id, children)
        rel = relation(fused)
        relative_children = [
            child
            for child in children.get(fused["id"], [])
            if relation(child) in {"acl:relcl", "advcl:relcl"}
        ]
        if lemma(fused) == "wherever" and any(
            relation(child) == "advcl:relcl" for child in relative_children
        ):
            specs.extend(
                [
                    spec(
                        dimension="clause_type",
                        answer="Place / free-choice adverbial clause",
                        target_words=target,
                        text=text,
                        confidence=0.94,
                        rule_id="clause-place-free-choice-adverbial",
                    ),
                    spec(
                        dimension="clause_structure",
                        answer="Finite wh-clause",
                        target_words=target,
                        text=text,
                        confidence=0.93,
                        rule_id="structure-finite-wh",
                    ),
                    spec(
                        dimension="clause_function",
                        answer="A — Adverbial",
                        target_words=target,
                        text=text,
                        confidence=0.94,
                        rule_id="function-clause-adverbial",
                    ),
                ]
            )
        elif rel in {"nsubj", "nsubj:pass", "csubj"}:
            specs.extend(
                [
                    spec(
                        dimension="clause_type",
                        answer="Nominal relative clause — function: S",
                        target_words=target,
                        text=text,
                        confidence=0.95,
                        rule_id="clause-nominal-relative-subject",
                    ),
                    spec(
                        dimension="clause_structure",
                        answer="Finite wh-clause",
                        target_words=target,
                        text=text,
                        confidence=0.94,
                        rule_id="structure-finite-wh",
                    ),
                    spec(
                        dimension="clause_function",
                        answer="S — Subject",
                        target_words=target,
                        text=text,
                        confidence=0.95,
                        rule_id="function-clause-subject",
                    ),
                ]
            )
        elif rel == "root" and any(
            relation(child) == "cop" for child in children.get(fused["id"], [])
        ):
            target = predicative_fused_relative_words(fused, by_id, children)
            specs.extend(
                [
                    spec(
                        dimension="clause_structure",
                        answer="Finite wh-clause",
                        target_words=target,
                        text=text,
                        confidence=0.94,
                        rule_id="structure-finite-wh",
                    ),
                    spec(
                        dimension="clause_function",
                        answer="SC — Subject Complement",
                        target_words=target,
                        text=text,
                        confidence=0.93,
                        rule_id="function-clause-subject-complement",
                    ),
                ]
            )
        elif rel in {"obj", "xcomp"}:
            function = "OC / Clausal object" if rel == "xcomp" else "DO — Direct Object"
            specs.append(
                spec(
                    dimension="clause_function",
                    answer=function,
                    target_words=target,
                    text=text,
                    confidence=0.58,
                    rule_id=(
                        "function-clause-object-complement-review"
                        if rel == "xcomp"
                        else "function-clause-direct-object"
                    ),
                    review_status="needs-review",
                    review_reason=(
                        "A non-subject fused relative requires contextual confirmation "
                        "of its higher-clause function."
                    ),
                )
            )
        # Finite wh structure is safe even where higher function is not.
        if not any(
            item["dimension"] == "clause_structure"
            and item["answer"] == "Finite wh-clause"
            and item["target_spans"] == spans_from_words(target, text)
            for item in specs
        ):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Finite wh-clause",
                    target_words=target,
                    text=text,
                    confidence=0.93,
                    rule_id="structure-finite-wh",
                )
            )

    clause_heads = [
        word
        for word in words
        if relation(word) in CLAUSE_RELATIONS
        and word not in fused_heads
        and word.get("head") not in fused_head_ids
    ]
    for head in clause_heads:
        rel = relation(head)
        parent = by_id.get(head.get("head"))
        markers = marker_words(head, children)
        phrase = marker_phrase(head, children)
        relative_like = rel in {"acl:relcl", "advcl:relcl"} or (
            rel == "acl"
            and not markers
            and any(
                (item.get("xpos") or "").startswith("W")
                or lemma(item) in RELATIVE_PRONOUNS | RELATIVE_ADVERBS
                for item in subtree_words(head["id"], by_id, children)
            )
        )
        target = (
            relative_clause_words(head, by_id, children)
            if relative_like
            else clause_words(head, by_id, children)
        )
        if (
            rel == "root"
            and markers
            and any(
                relation(child) == "nsubj:outer"
                for child in children.get(head["id"], [])
            )
            and any(
                relation(child) == "cop"
                for child in children.get(head["id"], [])
            )
        ):
            target = predicative_clause_words(head, by_id, children)

        # Marker type is separate from clause type, structure, and function.
        for marker in markers:
            marker_lemma = lemma(marker)
            if (
                relative_like
                and marker_lemma in RELATIVE_PRONOUNS | RELATIVE_ADVERBS
            ):
                continue
            if marker_lemma == "that" and rel != "advcl":
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Complementizer",
                        target_words=[marker],
                        text=text,
                        confidence=0.97,
                        rule_id="marker-complementizer",
                    )
                )
            elif marker_lemma == "whether":
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Interrogative subordinator",
                        target_words=[marker],
                        text=text,
                        confidence=0.97,
                        rule_id="marker-interrogative-whether",
                    )
                )
            elif marker_lemma == "if" and rel != "advcl":
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Interrogative subordinator",
                        target_words=[marker],
                        text=text,
                        confidence=0.60,
                        rule_id="marker-interrogative-if-review",
                        review_status="needs-review",
                        review_reason=(
                            "Embedded interrogative if must be distinguished from "
                            "conditional if using the higher construction."
                        ),
                    )
                )
            elif marker_lemma == "to":
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Infinitival marker",
                        target_words=[marker],
                        text=text,
                        confidence=0.98,
                        rule_id="marker-infinitival",
                    )
                )
            elif (
                marker_lemma in PREPOSITIONAL_ING_MARKERS
                and head.get("xpos") == "VBG"
            ):
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Preposition",
                        target_words=[marker],
                        text=text,
                        confidence=0.96,
                        rule_id="marker-preposition-ing",
                    )
                )
            elif rel in {"advcl", "advcl:relcl"}:
                specs.append(
                    spec(
                        dimension="clause_marker",
                        answer="Subordinating conjunction",
                        target_words=[marker],
                        text=text,
                        confidence=0.95,
                        rule_id="marker-subordinating-conjunction",
                    )
                )

        if relative_like:
            specs.extend(relative_marker_spec(head, by_id, children, text))

        # Structure.
        if "that" in phrase.split() and has_finite_verb(head, children):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Finite that-clause",
                    target_words=target,
                    text=text,
                    confidence=0.96,
                    rule_id="structure-finite-that",
                )
            )
        elif any(item in phrase.split() for item in {"whether", "if"}) and has_finite_verb(head, children):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Finite whether/if-clause",
                    target_words=target,
                    text=text,
                    confidence=0.95,
                    rule_id="structure-finite-whether-if",
                )
            )
        elif phrase == "to" and head.get("xpos") == "VB":
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="To-infinitival clause",
                    target_words=target,
                    text=text,
                    confidence=0.97,
                    rule_id="structure-to-infinitive",
                )
            )
        elif (
            rel == "xcomp"
            and head.get("xpos") == "VB"
            and not markers
        ):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Bare infinitival clause",
                    target_words=target,
                    text=text,
                    confidence=0.61,
                    rule_id="structure-bare-infinitive-review",
                    review_status="needs-review",
                    review_reason=(
                        "A bare infinitive after a perception or causative verb "
                        "requires confirmation against the teaching analysis."
                    ),
                )
            )
        elif head.get("xpos") == "VBG":
            prepositional = any(
                item in PREPOSITIONAL_ING_MARKERS for item in phrase.split()
            )
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer=(
                        "Preposition + -ing clause" if prepositional else "-ing clause"
                    ),
                    target_words=target,
                    text=text,
                    confidence=0.95,
                    rule_id=(
                        "structure-preposition-ing"
                        if prepositional
                        else "structure-ing"
                    ),
                )
            )
        elif (
            rel == "advcl"
            and head.get("upos") in {"ADJ", "ADV"}
            and not has_finite_verb(head, children)
        ):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Reduced / verbless clause",
                    target_words=target,
                    text=text,
                    confidence=0.58,
                    rule_id="structure-reduced-review",
                    review_status="needs-review",
                    review_reason=(
                        "Reduced adjective-based clauses are not represented "
                        "consistently by automatic dependency parses."
                    ),
                )
            )
        elif (
            rel == "ccomp"
            and parent
            and parent.get("upos") == "VERB"
            and not markers
            and has_finite_verb(head, children)
        ):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Finite zero-that clause",
                    target_words=target,
                    text=text,
                    confidence=0.93,
                    rule_id="structure-finite-zero-that",
                )
            )
        if comparative_pattern(head, by_id, children):
            specs.append(
                spec(
                    dimension="clause_structure",
                    answer="Comparative clause",
                    target_words=target,
                    text=text,
                    confidence=0.62,
                    rule_id="structure-comparative-review",
                    review_status="needs-review",
                    review_reason=(
                        "Comparative clause boundaries and attachment require "
                        "confirmation beyond the dependency relation."
                    ),
                )
            )

        # Clause type and higher function.
        if rel == "csubj":
            if phrase == "whether":
                specs.append(
                    spec(
                        dimension="clause_type",
                        answer="Dependent verbal question — function: S",
                        target_words=target,
                        text=text,
                        confidence=0.94,
                        rule_id="clause-dependent-question-subject",
                    )
                )
            specs.append(
                spec(
                    dimension="clause_function",
                    answer="S — Subject",
                    target_words=target,
                    text=text,
                    confidence=0.96,
                    rule_id="function-clause-subject",
                )
            )
        elif rel == "ccomp" and parent:
            if parent.get("upos") == "VERB":
                status = (
                    "auto-high-confidence"
                    if lemma(parent) in CONTENT_OBJECT_VERBS
                    else "needs-review"
                )
                specs.extend(
                    [
                        spec(
                            dimension="clause_type",
                            answer="Nominal clause — function: DO",
                            target_words=target,
                            text=text,
                            confidence=0.92 if status == "auto-high-confidence" else 0.58,
                            rule_id="clause-nominal-do",
                            review_status=status,
                            review_reason=(
                                None
                                if status == "auto-high-confidence"
                                else "The matrix predicate does not support an automatic nominal-DO classification."
                            ),
                        ),
                        spec(
                            dimension="clause_function",
                            answer="DO — Direct Object",
                            target_words=target,
                            text=text,
                            confidence=0.92 if status == "auto-high-confidence" else 0.58,
                            rule_id="function-clause-direct-object",
                            review_status=status,
                            review_reason=(
                                None
                                if status == "auto-high-confidence"
                                else "The higher-clause function depends on the matrix predicate."
                            ),
                        ),
                    ]
                )
                coordinated = [
                    child
                    for child in children.get(head["id"], [])
                    if relation(child) == "conj"
                    and (
                        marker_words(child, children)
                        or any(
                            relation(grandchild)
                            in {"nsubj", "nsubj:pass", "nsubj:outer"}
                            for grandchild in children.get(child["id"], [])
                        )
                    )
                ]
                if coordinated and status == "auto-high-confidence":
                    spans = spans_from_words(target, text)
                    for conjunct in coordinated:
                        spans.extend(
                            spans_from_words(
                                clause_words(conjunct, by_id, children),
                                text,
                            )
                        )
                    specs.append(
                        spec(
                            dimension="clause_type",
                            answer="Nominal clause — function: DO",
                            target_words=[],
                            target_spans=sorted(
                                spans, key=lambda span: (span["start"], span["end"])
                            ),
                            text=text,
                            confidence=0.91,
                            rule_id="clause-nominal-do",
                        )
                    )
            elif parent.get("upos") == "ADJ":
                specs.append(
                    spec(
                        dimension="clause_type",
                        answer="Nominal clause — postmodifier of an adjective",
                        target_words=target,
                        text=text,
                        confidence=0.92,
                        rule_id="clause-nominal-adjective-postmodifier",
                    )
                )
        elif rel == "acl" and parent and lemma(parent) in CONTENT_NOUNS and phrase in {"that", "whether"}:
            specs.append(
                spec(
                    dimension="clause_type",
                    answer="Appositive clause",
                    target_words=target,
                    text=text,
                    confidence=0.92,
                    rule_id="clause-appositive",
                )
            )
        elif rel == "advcl":
            if comparative_pattern(head, by_id, children):
                specs.extend(
                    [
                        spec(
                            dimension="clause_type",
                            answer="Comparative clause — postmodifier of an adjective",
                            target_words=target,
                            text=text,
                            confidence=0.92,
                            rule_id="clause-comparative-adjective-postmodifier",
                        ),
                        spec(
                            dimension="clause_function",
                            answer="PostM — Postmodifier",
                            target_words=target,
                            text=text,
                            confidence=0.91,
                            rule_id="function-clause-postmodifier",
                        ),
                    ]
                )
            else:
                answer, rule_id, status, confidence, reason = adverbial_type(
                    head, by_id, children
                )
                specs.extend(
                    [
                        spec(
                            dimension="clause_type",
                            answer=answer,
                            target_words=target,
                            text=text,
                            confidence=confidence,
                            rule_id=rule_id,
                            review_status=status,
                            review_reason=reason,
                        ),
                        spec(
                            dimension="clause_function",
                            answer="A — Adverbial",
                            target_words=target,
                            text=text,
                            confidence=0.93 if markers else 0.61,
                            rule_id="function-clause-adverbial",
                            review_status=(
                                "auto-high-confidence" if markers else "needs-review"
                            ),
                            review_reason=(
                                None
                                if markers
                                else "An unmarked supplementive clause requires review before assigning A."
                            ),
                        ),
                    ]
                )
        elif relative_like and parent:
            rel_words = relative_clause_words(head, by_id, children)
            rel_spans = spans_from_words(rel_words, text)
            start = rel_spans[0]["start"] if rel_spans else 0
            end = rel_spans[-1]["end"] if rel_spans else 0
            before = text[max(0, start - 3):start]
            after = text[end:min(len(text), end + 3)]
            comma_delimited = "," in before and "," in after
            wh_lemmas = {
                lemma(item)
                for item in rel_words
                if (item.get("xpos") or "").startswith("W")
            }
            zero_relative = not wh_lemmas
            semantic_exception = (
                lemma(parent) in TEMPORAL_RELATIVE_HOSTS
                and "which" in wh_lemmas
                and any(relation(child) == "cop" for child in children.get(head["id"], []))
                and not comma_delimited
            )
            if comma_delimited:
                answer = "Non-restrictive relative clause — function: PostM"
                rule_id = "clause-relative-nonrestrictive"
                status, confidence, reason = "auto-high-confidence", 0.94, None
            elif semantic_exception:
                answer = "Non-restrictive relative clause — function: PostM"
                rule_id = "clause-relative-semantic-review"
                status, confidence = "needs-review", 0.57
                reason = (
                    "Punctuation does not encode the reviewed non-restrictive "
                    "reading; semantic interpretation is required."
                )
            elif zero_relative:
                answer = (
                    "Restrictive relative clause — function: PostM"
                    if head.get("upos") == "VERB"
                    else "Relative clause — function: PostM"
                )
                rule_id = "clause-relative-zero-review"
                status, confidence = "needs-review", 0.60
                reason = "Zero-relative recovery and restrictiveness require review."
            elif wh_lemmas & {"why", "where"} or any(
                relation(item) == "case" and item in rel_words for item in rel_words
            ):
                answer = "Relative clause — function: PostM"
                rule_id = "clause-relative-generic"
                status, confidence, reason = "auto-high-confidence", 0.92, None
            else:
                answer = "Restrictive relative clause — function: PostM"
                rule_id = "clause-relative-restrictive"
                status, confidence, reason = "auto-high-confidence", 0.92, None
            specs.extend(
                [
                    spec(
                        dimension="clause_type",
                        answer=answer,
                        target_words=rel_words,
                        text=text,
                        confidence=confidence,
                        rule_id=rule_id,
                        review_status=status,
                        review_reason=reason,
                        event_variant=(
                            (
                                "clause-head-verb"
                                if head.get("upos") == "VERB"
                                else "clause-head-nonverb"
                            )
                            if zero_relative
                            else None
                        ),
                    ),
                    spec(
                        dimension="clause_function",
                        answer="PostM — Postmodifier",
                        target_words=rel_words,
                        text=text,
                        confidence=0.94,
                        rule_id="function-clause-postmodifier",
                    ),
                ]
            )
        elif rel == "xcomp" and parent:
            objects = [
                child
                for child in children.get(parent["id"], [])
                if relation(child) in {"obj", "iobj"}
            ]
            if objects and (
                parent and lemma(parent) in PERCEPTION_VERBS | COMPLEX_TRANSITIVE_VERBS
            ):
                specs.append(
                    spec(
                        dimension="clause_function",
                        answer="OC / Clausal object",
                        target_words=target,
                        text=text,
                        confidence=0.60,
                        rule_id="function-clause-object-complement-review",
                        review_status="needs-review",
                        review_reason=(
                            "The non-finite clause can be analysed as OC or a "
                            "clausal object depending on the teaching convention."
                        ),
                    )
                )

        # Predicative content clauses may be Stanza roots with outer subjects.
        if rel == "root" and phrase in {"that", "whether", "if"}:
            outer_subject = any(
                relation(child) == "nsubj:outer"
                for child in children.get(head["id"], [])
            )
            copular = any(
                relation(child) == "cop" for child in children.get(head["id"], [])
            )
            if outer_subject and copular:
                specs.extend(
                    [
                        spec(
                            dimension="clause_type",
                            answer="Nominal clause — function: SC",
                            target_words=predicative_clause_words(head, by_id, children),
                            text=text,
                            confidence=0.93,
                            rule_id="clause-nominal-subject-complement",
                        ),
                        spec(
                            dimension="clause_function",
                            answer="SC — Subject Complement",
                            target_words=predicative_clause_words(head, by_id, children),
                            text=text,
                            confidence=0.93,
                            rule_id="function-clause-subject-complement",
                        ),
                    ]
                )

    return deduplicate(specs)


def anchored_case_ids() -> set[str]:
    return {
        case_id
        for case_ids in RULE_ANCHORS.values()
        for case_id in case_ids
    }
