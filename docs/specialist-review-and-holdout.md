# Specialist review and next encoder experiment

Status: ready for reviewer assignment. No incident is newly specialist-approved by this preparation. The existing 16 drafts were inspected during development and cannot become an independent holdout by relabeling them.

## Review pack

Open [the blind incident pack](review/workflow-drafts/review.md). Each case shows the current observations, decision time, impact, topology, change information, and policy. It omits draft answers, author rationales, and model results. Complete [responses.json](review/workflow-drafts/responses.json) with a reviewer name and network operations experience, case decisions, accepted alternatives, and rationale. For a revision, state the input correction needed. Unknown facts should remain unknown.

The eight paired mechanisms cover mixed current/stale evidence, queue discard and its negation, verified recovery, contradictory measurements, shared-service evidence, maintenance scope, unrelated changes, and dependency membership. Review each variant separately before inspecting the pair and check that the intervention really changes only intended evidence. Mixed `none` or `unknown` impact should receive special attention: confirm whether stated impact and reference policy can coexist with the narrative.

Validate a completed response file with:

```bash
python3 scripts/prepare_specialist_review.py --responses docs/review/workflow-drafts/responses.json
```

The validator checks completeness, allowed answers, and priority consistency. Approval requires unchanged inputs; use `revise` when corrections are needed. It does not authenticate reviewer expertise, resolve disagreements, edit labels, or train a model. A partial review stays partial. Conflicts between approved reviewers need adjudication rather than silently combining incompatible alternatives.

After adjudication, write a versioned reviewed development release with revised inputs where needed, final labels, review provenance, and new hashes. Preserve original drafts and prediction snapshots. Do not score old predictions against corrected inputs as if they were generated from those inputs. Accepted alternatives are set per field in the existing scorer; if alternatives have cross-field dependencies, extend the scoring format before using them.

## Training and development

The first encoder head remains frozen. The next candidate should learn explicit distinctions between positive, negative, and conflicting domain evidence, verified recovery, and relevant versus unrelated changes. Add new reviewed training families and use a separate family-disjoint development cohort to choose features, regularization, or end-to-end training. Keep all paired variants and paraphrases of one mechanism in a single split.

Include training cases in which the same domain terms appear with opposite evidentiary meaning, plus cases with current normal measurements alongside stale alarms. Do not repair errors solely by adding the evaluated draft pairs to training and rerunning them. If these reviewed drafts enter training, they cease to measure that candidate's generalization.

The current renderer omits timestamps and graph edges. Decide before training whether the encoder should use structured freshness and dependency features. Such a model is an encoder-plus-structured-feature configuration and needs a new protocol identity. Its gains should be compared with the existing encoder and Jev candidates on the same approved cohort.

## New holdout

Assign an operations specialist to author or select unseen incident families after candidate selection. Aim for at least 30 distinct holdout mechanisms as a planning target, not a guarantee of statistical precision. Separate the realistic incident-mix cohort from a deliberately balanced paired stress cohort. Group correlated incidents from the same outage, shared cause, or mechanism into one split.

Review incident inputs and labels against evidence available at decision time. Future restoration logs, final diagnosis, and analyst hindsight must not enter prediction inputs. Label a justified initial investigation route and next diagnostic action, not the eventual root cause. Keep label artifacts under a reviewer-controlled path until predictions and candidate hashes are frozen.

Before running holdout, record model/head, renderer, prompt, composer, policy, thresholds, dependency versions, and input hashes. Record prediction hashes before opening answer keys. If developers inspect or tune against holdout labels or misses, treat that cohort as development and reserve new unseen families.

Report complete-decision accuracy, field metrics, severe-priority errors, false domain assignments, false monitoring, pair consistency, and error at matched automation coverage. Select thresholds using development data only. A model's evidence-insufficient flag is not a calibrated error predictor.

## Required next input

A named network operations reviewer must complete and adjudicate the development draft review before these labels are used as specialist-approved training data. A separate unseen cohort is still needed for a holdout claim. The code and review pack are ready; this document does not imply that review or new data collection has occurred.
