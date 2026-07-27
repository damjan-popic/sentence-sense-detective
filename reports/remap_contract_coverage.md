# Formal remap contract coverage

- Profile: `en-1.0.0`
- Source workbook SHA-256: `f62fcfcdc35d43d8425b63266b86ae54c3bd688d37ca5e47e0dab432f767a51d`
- Formal rules: 99
- Contract-backed rules: 85
- Provisional POS rules: 14
- Contract cases: 106
- Covered publishable: 82
- Covered manual guard: 20
- Parser mismatch: 0
- Unresolved teacher comments: 4

## Cases

| Case | Expected decision | Status | Rule IDs | Teacher-comment disposition |
|---|---|---|---|---|
| SE-S-01 | OK | covered_publishable | `se.subject.np` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-S-02 | Rule-based OK | covered_publishable | `se.subject.np` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-S-03 | OK | covered_publishable | `se.subject.clause` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-S-04 | OK | covered_publishable | `se.subject.clause` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-S-05 | OK | covered_publishable | `se.subject.clause` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-S-06 | Needs manual review | covered_manual_guard | `se.formal.postponed.subject` | Implemented as an explicit review guard. |
| SE-P-01 | OK | covered_publishable | `se.predicator.simple` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-P-02 | Rule-based OK | covered_publishable | `se.operator.finite.auxiliary` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-P-03 | Rule-based OK | covered_publishable | `se.predicator.passive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-P-04 | Rule-based OK | covered_publishable | `se.predicator.copula` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-P-05 | Rule-based OK | covered_publishable | `se.predicator.particle` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-01 | OK | covered_publishable | `se.direct.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-02 | OK | covered_publishable | `se.direct.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-03 | Rule-based OK | covered_publishable | `se.direct.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-04 | Rule-based OK | covered_publishable | `se.clausal.direct.object.publish`, `se.clausal.direct.object.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-05 | Rule-based OK | covered_publishable | `se.clausal.direct.object.publish`, `se.clausal.direct.object.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-06 | Rule-based OK | covered_publishable | `se.clausal.direct.object.publish`, `se.clausal.direct.object.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-DO-07 | Needs manual review | covered_manual_guard | `se.gerund.complement.review` | Implemented as an explicit review guard. |
| SE-IO-01 | OK | covered_publishable | `se.indirect.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-IO-02 | Rule-based OK | covered_publishable | `se.indirect.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-IO-03 | OK | covered_publishable | `se.indirect.object` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-01 | Rule-based OK | covered_publishable | `se.subject.complement.copular` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-02 | Rule-based OK | covered_publishable | `se.subject.complement.copular` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-03 | Rule-based OK | covered_publishable | `se.subject.complement.copular` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-04 | Rule-based OK | covered_publishable | `se.subject.complement.copular` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-05 | Rule-based OK | unresolved_teacher_comment | `se.subject.complement.copular` | Martin's comment is only “#9”; its intended referent is not recoverable from the supplied extraction. |
| SE-SC-06 | Rule-based OK | covered_publishable | `se.subject.complement.copular` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-07 | Rule-based OK | covered_publishable | `se.subject.complement.linking` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-SC-08 | Rule-based OK | covered_publishable | `se.subject.complement.linking` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-OC-01 | Rule-based OK | covered_publishable | `se.object.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-OC-02 | Rule-based OK | covered_publishable | `se.object.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-OC-03 | Rule-based OK | covered_publishable | `se.object.complement.pp.definite`, `se.object.complement.pp.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-OC-04 | Needs manual review | covered_manual_guard | `se.object.complement.bare.review` | Implemented as an explicit review guard. |
| SE-OC-05 | Rule-based OK | covered_publishable | `se.object.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-OC-06 | Rule-based OK | covered_publishable | `se.object.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-01 | OK | covered_publishable | `se.adverbial.direct` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-02 | Rule-based OK | covered_publishable | `se.adverbial.direct` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-03 | Needs manual review | covered_manual_guard | `se.adverbial.duration.review` | Implemented as an explicit review guard. |
| SE-A-04 | OK | covered_publishable | `se.adverbial.direct` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-05 | Rule-based OK | covered_publishable | `se.two.adverbials` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-06 | Rule-based OK | covered_publishable | `se.adverbial.clause.publish`, `se.adverbial.clause.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| SE-A-07 | Rule-based OK | covered_publishable | `se.adverbial.clause.publish`, `se.adverbial.clause.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MAIN-01 | OK | covered_publishable | `clause.main`, `clause.main.complex.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-01 | Rule-based OK | covered_publishable | `clause.nominal.do.publish`, `clause.nominal.do.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-02 | Rule-based OK | covered_publishable | `clause.nominal.do.publish`, `clause.nominal.do.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-03 | Rule-based OK | covered_publishable | `clause.nominal.do.publish`, `clause.nominal.do.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-04 | Rule-based OK | covered_publishable | `clause.nominal.relative.subject` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-05 | Rule-based OK | covered_publishable | `clause.dependent.question.subject` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-06 | Rule-based OK | covered_publishable | `clause.appositive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-07 | Rule-based OK | covered_publishable | `clause.appositive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-08 | Rule-based OK | covered_publishable | `clause.nominal.subject.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-NOM-09 | Needs manual review | covered_manual_guard | `clause.nominal.adjective.postmodifier` | Implemented as an explicit review guard. |
| CL-NOM-10 | Needs manual review | covered_manual_guard | `clause.nominal.adjective.postmodifier` | Implemented as an explicit review guard. |
| CL-ADV-01 | Rule-based OK | covered_publishable | `clause.temporal.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-02 | Rule-based OK | covered_publishable | `clause.causal.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-03 | Rule-based OK | covered_publishable | `clause.causal.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-04 | Rule-based OK | covered_publishable | `clause.conditional.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-05 | Rule-based OK | covered_publishable | `clause.negative.conditional.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-06 | Rule-based OK | covered_publishable | `clause.concessive.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-07 | Rule-based OK | covered_publishable | `clause.purpose.adverbial.publish`, `clause.purpose.adverbial.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-08 | Rule-based OK | covered_publishable | `clause.place.free.choice.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-09 | Rule-based OK | covered_publishable | `clause.manner.comparison.adverbial` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-10 | Needs manual review | covered_manual_guard | `clause.comparative.adjective.postmodifier` | Implemented as an explicit review guard. |
| CL-ADV-11 | Rule-based OK | covered_publishable | `clause.supplementive.initial`, `clause.supplementive.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-12 | Rule-based OK | covered_publishable | `clause.generic.adverbial.publish` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-13 | Rule-based OK | covered_publishable | `clause.generic.adverbial.publish` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-ADV-14 | Needs manual review | covered_manual_guard | `clause.generic.adverbial.review` | Implemented as an explicit review guard. |
| CL-ADV-15 | Needs manual review | covered_manual_guard | `clause.generic.adverbial.review` | Implemented as an explicit review guard. |
| CL-REL-01 | Rule-based OK | covered_publishable | `clause.relative.restrictive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-02 | Needs manual review | covered_manual_guard | `clause.relative.zero.review.review.relative-clause-function-postm-zero-relati`, `clause.relative.zero.review.review.restrictive-relative-clause-function-postm` | Implemented as an explicit review guard. |
| CL-REL-03 | Rule-based OK | covered_publishable | `clause.relative.generic` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-04 | Rule-based OK | covered_publishable | `clause.relative.generic` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-05 | Rule-based OK | covered_publishable | `clause.relative.generic` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-06 | Rule-based OK | covered_publishable | `clause.relative.restrictive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-07 | Needs manual review | covered_manual_guard | `clause.relative.zero.review.review.relative-clause-function-postm-zero-relati`, `clause.relative.zero.review.review.restrictive-relative-clause-function-postm` | Implemented as an explicit review guard. |
| CL-REL-08 | Rule-based OK | covered_publishable | `clause.relative.restrictive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-09 | Rule-based OK | covered_publishable | `clause.relative.nonrestrictive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-REL-10 | Needs manual review | covered_manual_guard | `clause.relative.semantic.review` | Implemented as an explicit review guard. |
| CL-MARK-01 | OK | unresolved_teacher_comment | `marker.complementizer` | Martin's comment says he does not understand source items #82–#92; the supplied extraction contains no more specific correction. |
| CL-MARK-02 | OK | covered_publishable | `marker.interrogative.whether` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-03 | Needs manual review | covered_manual_guard | `marker.interrogative.if.review` | Implemented as an explicit review guard. |
| CL-MARK-04 | OK | covered_publishable | `marker.subordinating.conjunction` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-05 | OK | covered_publishable | `marker.subordinating.conjunction` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-06 | OK | covered_publishable | `marker.subordinating.conjunction` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-07 | OK | covered_publishable | `marker.relative.pronoun` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-08 | OK | covered_publishable | `marker.relative.adverb` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-09 | OK | covered_publishable | `marker.infinitival` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-MARK-10 | Needs manual review | covered_manual_guard | `marker.zero.not.highlightable` | Implemented as an explicit review guard. |
| CL-STR-01 | Rule-based OK | unresolved_teacher_comment | `structure.finite.that` | The comment “ditto @ #93-#102” points to an unresolved source-level comment rather than a formal terminology correction. |
| CL-STR-02 | Rule-based OK | covered_publishable | `structure.finite.zero.that` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-03 | OK | covered_publishable | `structure.finite.wh` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-04 | OK | covered_publishable | `structure.finite.whether.if` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-05 | OK | covered_publishable | `structure.to.infinitive` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-06 | Needs manual review | covered_manual_guard | `structure.bare.infinitive.review` | Implemented as an explicit review guard. |
| CL-STR-07 | OK | covered_publishable | `structure.ing` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-08 | OK | covered_publishable | `marker.preposition.ing`, `structure.preposition.ing` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-STR-09 | Needs manual review | covered_manual_guard | `structure.reduced.review` | Implemented as an explicit review guard. |
| CL-STR-10 | Needs manual review | covered_manual_guard | `structure.comparative.review` | Implemented as an explicit review guard. |
| CL-FUNC-01 | OK | unresolved_teacher_comment | `function.clause.subject` | The comment “ditto @ #103-#108” points to an unresolved source-level comment rather than a formal terminology correction. |
| CL-FUNC-02 | Rule-based OK | covered_publishable | `function.clause.direct.object.publish`, `function.clause.direct.object.review.do-direct-object-a-non-subject-fused-relat`, `function.clause.direct.object.review.do-direct-object-the-higher-clause-functio` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-FUNC-03 | Rule-based OK | covered_publishable | `function.clause.subject.complement` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-FUNC-04 | Rule-based OK | covered_publishable | `function.clause.adverbial.publish`, `function.clause.adverbial.review` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-FUNC-05 | Rule-based OK | covered_publishable | `function.clause.postmodifier` | Implemented in the rule output, structural condition, exclusion, or dimension separation. |
| CL-FUNC-06 | Needs manual review | covered_manual_guard | `function.clause.object.complement.review.review.oc-clausal-object-a-non-subject-fused-rela`, `function.clause.object.complement.review.review.oc-clausal-object-the-non-finite-clause-ca` | Implemented as an explicit review guard. |
| REVIEW-01 | Needs manual review | covered_manual_guard | `se.ambiguous.pp.review.review.a-adverbial-a-technical-oblique-relation-d`, `se.ambiguous.pp.review.review.context-needed-pp-attachment-is-ambiguous-` | Implemented as an explicit review guard. |
| REVIEW-02 | Needs manual review | covered_manual_guard | `se.copular.temporal.review` | Implemented as an explicit review guard. |
