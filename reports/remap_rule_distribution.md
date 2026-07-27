# Formal remap rule distribution

- Profile: `en-1.0.0`
- Sentences: 10000
- Formal candidates before presentation selection: 274198
- Presented question candidates: 119261
- Publishable formal candidates: 257084
- Review-only formal candidates: 17114
- Conflict downgrades: 194
- Rules with at least one 10K match: 96
- Rules without a 10K match: 3

## Per-rule counts

| Rule | Dimension | Decision | Configured action | Matches | Publish | Review | Conflicts |
|---|---|---|---|---:|---:|---:|---:|
| `clause.appositive` | clause_type | rule-based | publish | 42 | 42 | 0 | 0 |
| `clause.causal.adverbial` | clause_type | rule-based | publish | 106 | 106 | 0 | 0 |
| `clause.comparative.adjective.postmodifier` | clause_type | manual-review | review | 16 | 0 | 16 | 0 |
| `clause.concessive.adverbial` | clause_type | rule-based | publish | 113 | 113 | 0 | 0 |
| `clause.conditional.adverbial` | clause_type | rule-based | publish | 287 | 287 | 0 | 0 |
| `clause.dependent.question.subject` | clause_type | rule-based | publish | 1 | 1 | 0 | 0 |
| `clause.generic.adverbial.publish` | clause_type | rule-based | publish | 2175 | 2175 | 0 | 0 |
| `clause.generic.adverbial.review` | clause_type | manual-review | review | 107 | 0 | 107 | 0 |
| `clause.main` | clause_type | direct | publish | 8292 | 8292 | 0 | 0 |
| `clause.main.complex.review` | clause_type | manual-review | review | 1215 | 0 | 1215 | 0 |
| `clause.manner.comparison.adverbial` | clause_type | rule-based | publish | 14 | 14 | 0 | 0 |
| `clause.negative.conditional.adverbial` | clause_type | rule-based | publish | 9 | 9 | 0 | 0 |
| `clause.nominal.adjective.postmodifier` | clause_type | manual-review | review | 75 | 0 | 75 | 0 |
| `clause.nominal.do.publish` | clause_type | rule-based | publish | 1111 | 1111 | 0 | 0 |
| `clause.nominal.do.review` | clause_type | manual-review | review | 406 | 0 | 406 | 0 |
| `clause.nominal.relative.subject` | clause_type | rule-based | publish | 20 | 20 | 0 | 0 |
| `clause.nominal.subject.complement` | clause_type | rule-based | publish | 54 | 54 | 0 | 0 |
| `clause.place.free.choice.adverbial` | clause_type | rule-based | publish | 2 | 2 | 0 | 0 |
| `clause.purpose.adverbial.publish` | clause_type | rule-based | publish | 15 | 15 | 0 | 0 |
| `clause.purpose.adverbial.review` | clause_type | manual-review | review | 11 | 0 | 11 | 0 |
| `clause.relative.generic` | clause_type | rule-based | publish | 1018 | 1018 | 0 | 0 |
| `clause.relative.nonrestrictive` | clause_type | rule-based | publish | 84 | 84 | 0 | 0 |
| `clause.relative.restrictive` | clause_type | rule-based | publish | 431 | 431 | 0 | 0 |
| `clause.relative.semantic.review` | clause_type | manual-review | review | 1 | 0 | 1 | 0 |
| `clause.relative.zero.review.review.relative-clause-function-postm-zero-relati` | clause_type | manual-review | review | 42 | 0 | 42 | 0 |
| `clause.relative.zero.review.review.restrictive-relative-clause-function-postm` | clause_type | manual-review | review | 421 | 0 | 421 | 0 |
| `clause.supplementive.initial` | clause_type | rule-based | publish | 40 | 40 | 0 | 0 |
| `clause.supplementive.review` | clause_type | manual-review | review | 382 | 0 | 382 | 0 |
| `clause.temporal.adverbial` | clause_type | rule-based | publish | 148 | 148 | 0 | 0 |
| `function.clause.adverbial.publish` | clause_function | rule-based | publish | 2516 | 2516 | 0 | 0 |
| `function.clause.adverbial.review` | clause_function | manual-review | review | 893 | 0 | 893 | 0 |
| `function.clause.direct.object.publish` | clause_function | rule-based | publish | 1078 | 1078 | 0 | 0 |
| `function.clause.direct.object.review.do-direct-object-a-non-subject-fused-relat` | clause_function | manual-review | review | 53 | 0 | 53 | 0 |
| `function.clause.direct.object.review.do-direct-object-the-higher-clause-functio` | clause_function | manual-review | review | 406 | 0 | 406 | 0 |
| `function.clause.object.complement.review.review.oc-clausal-object-a-non-subject-fused-rela` | clause_function | manual-review | review | 0 | 0 | 0 | 0 |
| `function.clause.object.complement.review.review.oc-clausal-object-the-non-finite-clause-ca` | clause_function | manual-review | review | 208 | 0 | 208 | 0 |
| `function.clause.postmodifier` | clause_function | rule-based | publish | 2013 | 2013 | 0 | 0 |
| `function.clause.subject` | clause_function | direct | publish | 273 | 273 | 0 | 0 |
| `function.clause.subject.complement` | clause_function | rule-based | publish | 70 | 70 | 0 | 0 |
| `marker.complementizer` | clause_marker | direct | publish | 861 | 861 | 0 | 0 |
| `marker.infinitival` | clause_marker | direct | publish | 2908 | 2908 | 0 | 0 |
| `marker.interrogative.if.review` | clause_marker | manual-review | review | 46 | 0 | 46 | 0 |
| `marker.interrogative.whether` | clause_marker | direct | publish | 41 | 41 | 0 | 0 |
| `marker.preposition.ing` | clause_marker | direct | publish | 481 | 481 | 0 | 0 |
| `marker.relative.adverb` | clause_marker | direct | publish | 116 | 116 | 0 | 0 |
| `marker.relative.pronoun` | clause_marker | direct | publish | 1382 | 1382 | 0 | 0 |
| `marker.subordinating.conjunction` | clause_marker | direct | publish | 1553 | 1553 | 0 | 0 |
| `marker.zero.not.highlightable` | clause_marker | manual-review | review | 0 | 0 | 0 | 0 |
| `pos.adj` | word_class | rule-based | publish | 15746 | 15746 | 0 | 0 |
| `pos.adv` | word_class | rule-based | publish | 8049 | 8049 | 0 | 0 |
| `pos.cconj` | word_class | rule-based | publish | 6903 | 6903 | 0 | 0 |
| `pos.det` | word_class | rule-based | publish | 18613 | 18613 | 0 | 0 |
| `pos.infinitival.marker` | word_class | rule-based | publish | 2698 | 2698 | 0 | 0 |
| `pos.lexical.verb` | word_class | rule-based | publish | 22133 | 22133 | 0 | 0 |
| `pos.modal.auxiliary` | word_class | rule-based | publish | 2548 | 2548 | 0 | 0 |
| `pos.noun` | word_class | rule-based | publish | 43246 | 43246 | 0 | 0 |
| `pos.particle` | word_class | rule-based | publish | 631 | 631 | 0 | 0 |
| `pos.preposition` | word_class | rule-based | publish | 21395 | 21395 | 0 | 0 |
| `pos.primary.auxiliary` | word_class | rule-based | publish | 4500 | 4500 | 0 | 0 |
| `pos.pron` | word_class | rule-based | publish | 13316 | 13316 | 0 | 0 |
| `pos.propn` | word_class | rule-based | publish | 11921 | 11921 | 0 | 0 |
| `pos.sconj` | word_class | rule-based | publish | 3237 | 3237 | 0 | 0 |
| `se.adverbial.clause.publish` | sentence_element | rule-based | publish | 2535 | 2535 | 0 | 0 |
| `se.adverbial.clause.review` | sentence_element | manual-review | review | 895 | 0 | 895 | 0 |
| `se.adverbial.direct` | sentence_element | rule-based | publish | 4023 | 4022 | 1 | 1 |
| `se.adverbial.duration.review` | sentence_element | manual-review | review | 720 | 0 | 720 | 4 |
| `se.ambiguous.pp.review.review.a-adverbial-a-technical-oblique-relation-d` | sentence_element | manual-review | review | 7197 | 0 | 7197 | 0 |
| `se.ambiguous.pp.review.review.context-needed-pp-attachment-is-ambiguous-` | sentence_element | manual-review | review | 2905 | 0 | 2905 | 81 |
| `se.clausal.direct.object.publish` | sentence_element | rule-based | publish | 1085 | 1085 | 0 | 0 |
| `se.clausal.direct.object.review` | sentence_element | manual-review | review | 406 | 0 | 406 | 0 |
| `se.copular.temporal.review` | sentence_element | manual-review | review | 30 | 0 | 30 | 0 |
| `se.direct.object` | sentence_element | rule-based | publish | 9090 | 9090 | 0 | 0 |
| `se.formal.postponed.subject` | sentence_element | manual-review | review | 158 | 0 | 158 | 0 |
| `se.gerund.complement.review` | sentence_element | manual-review | review | 59 | 0 | 59 | 5 |
| `se.indirect.object` | sentence_element | rule-based | publish | 328 | 328 | 0 | 0 |
| `se.object.complement` | sentence_element | rule-based | publish | 150 | 145 | 5 | 5 |
| `se.object.complement.bare.review` | sentence_element | manual-review | review | 14 | 0 | 14 | 0 |
| `se.object.complement.pp.definite` | sentence_element | rule-based | publish | 7 | 7 | 0 | 0 |
| `se.object.complement.pp.review` | sentence_element | manual-review | review | 86 | 0 | 86 | 86 |
| `se.operator.finite.auxiliary` | sentence_element | rule-based | publish | 2209 | 2209 | 0 | 0 |
| `se.predicator.copula` | sentence_element | rule-based | publish | 2120 | 2120 | 0 | 0 |
| `se.predicator.particle` | sentence_element | rule-based | publish | 175 | 175 | 0 | 0 |
| `se.predicator.passive` | sentence_element | rule-based | publish | 1143 | 1143 | 0 | 0 |
| `se.predicator.simple` | sentence_element | direct | publish | 6249 | 6249 | 0 | 0 |
| `se.subject.clause` | sentence_element | direct | publish | 570 | 570 | 0 | 0 |
| `se.subject.complement.copular` | sentence_element | rule-based | publish | 2070 | 2070 | 0 | 0 |
| `se.subject.complement.linking` | sentence_element | rule-based | publish | 203 | 203 | 0 | 0 |
| `se.subject.np` | sentence_element | rule-based | publish | 15803 | 15803 | 0 | 0 |
| `se.two.adverbials` | sentence_element | rule-based | publish | 0 | 0 | 0 | 0 |
| `structure.bare.infinitive.review` | clause_structure | manual-review | review | 237 | 0 | 237 | 0 |
| `structure.comparative.review` | clause_structure | manual-review | review | 16 | 0 | 16 | 6 |
| `structure.finite.that` | clause_structure | rule-based | publish | 920 | 920 | 0 | 0 |
| `structure.finite.wh` | clause_structure | direct | publish | 198 | 198 | 0 | 0 |
| `structure.finite.whether.if` | clause_structure | direct | publish | 377 | 377 | 0 | 0 |
| `structure.finite.zero.that` | clause_structure | rule-based | publish | 730 | 730 | 0 | 0 |
| `structure.ing` | clause_structure | direct | publish | 1976 | 1976 | 0 | 0 |
| `structure.preposition.ing` | clause_structure | direct | publish | 475 | 475 | 0 | 0 |
| `structure.reduced.review` | clause_structure | manual-review | review | 103 | 0 | 103 | 6 |
| `structure.to.infinitive` | clause_structure | direct | publish | 2464 | 2464 | 0 | 0 |
