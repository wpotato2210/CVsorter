# OpenSpec v3 Validation Plan

## Purpose

Define measurable, release-gating validation thresholds for OpenSpec v3 runtime performance, model quality, timing stability, and environmental robustness.

## Acceptance thresholds

### 1) Throughput

Throughput is measured in both mass flow and piece rate to support deployment-specific operating constraints.

| Metric | Definition | Acceptance threshold | Measurement window |
| --- | --- | --- | --- |
| Sustained throughput (kg/hr) | Net accepted + rejected material mass processed per hour, excluding startup/calibration | **>= 180 kg/hr** sustained | Minimum 60 min steady-state run |
| Peak throughput (kg/hr) | Highest 5 min rolling average mass flow while preserving quality thresholds | **>= 220 kg/hr** | 5 min rolling window |
| Sustained piece rate (pcs/min) | Total classified pieces per minute in steady-state | **>= 1,200 pcs/min** | Minimum 60 min steady-state run |
| Peak piece rate (pcs/min) | Highest 1 min rolling average piece rate while preserving quality thresholds | **>= 1,400 pcs/min** | 1 min rolling window |

### 2) Accuracy and classification quality

All quality metrics are macro-averaged across active sort classes and reported with 95% confidence intervals from the locked regression corpus.

| Metric | Acceptance threshold |
| --- | --- |
| Precision | **>= 0.965** |
| Recall | **>= 0.955** |
| F1 score | **>= 0.960** |
| False accept rate (FAR) | **<= 1.5%** |
| False reject rate (FRR) | **<= 2.5%** |

Additional quality constraints:
- FAR and FRR must each satisfy threshold on both global aggregate and each top-5 volume class.
- No class with >= 2% corpus prevalence may have F1 < 0.92.

### 3) End-to-end jitter

End-to-end jitter captures timing variation from frame ingress timestamp to actuator command emission timestamp.

| Metric | Acceptance threshold |
| --- | --- |
| P95 end-to-end latency jitter | **<= 12 ms** |
| P99 end-to-end latency jitter | **<= 18 ms** |
| Maximum single-sample jitter excursion | **<= 30 ms**, with at most 1 excursion per 100k frames |

### 4) Environmental robustness

Validation is executed under controlled environmental stressors relative to baseline conditions (500 lux diffuse lighting, clean optics, dry feedstock).

| Factor | Test levels | Acceptance threshold |
| --- | --- | --- |
| Lighting | 300 lux, 500 lux, 900 lux; + glare simulation | F1 degradation <= 1.5 percentage points vs baseline |
| Dust | Airborne particulate exposure at 0.5 mg/m³ and 1.0 mg/m³ equivalent | FAR increase <= 0.7 percentage points vs baseline |
| Moisture | Surface moisture at 0.5% and 1.0% by mass | FRR increase <= 1.0 percentage point vs baseline |

Cross-factor criteria:
- Under any single stress condition, throughput must remain >= 90% of baseline sustained rate.
- Under combined moderate stress (500 lux + 0.5 mg/m³ dust + 0.5% moisture), all core quality thresholds remain mandatory.

## Regression corpus policy

## Corpus composition

The locked regression corpus is versioned as `openspec-v3-regression-<date>` and includes:
- **Minimum 250,000 labeled frames** across production-representative classes.
- **Minimum 1.2 million object instances** with per-instance labels.
- Class-balance floor: each critical class >= 10,000 instances.
- Dedicated stress subsets for lighting, dust, and moisture scenarios.

## Dataset controls

- Train/validation/regression sets are disjoint at source batch level.
- Regression corpus is immutable within a release branch except for documented critical relabel patches.
- Any corpus revision must increment corpus version and trigger full baseline recomputation.

## CI gating rules

A pull request is merge-eligible only when all gates below pass:

1. **Metrics gate (blocking)**
   - Throughput, quality, FAR/FRR, and jitter thresholds meet or exceed this document.
   - Checked by automated benchmark + evaluation jobs.

2. **Regression drift gate (blocking)**
   - No metric may regress by > 0.5 percentage points (absolute) relative to current release baseline unless explicitly approved under a waiver.
   - Waiver requires maintainer sign-off and documented mitigation plan.

3. **Environmental robustness gate (blocking for release branches, warning on feature branches)**
   - Stress subset metrics satisfy robustness thresholds.

4. **Reproducibility gate (blocking)**
   - Two repeated CI runs on identical commit and corpus must match within:
     - F1 delta <= 0.2 percentage points
     - Throughput delta <= 3%
     - Jitter P95 delta <= 2 ms

5. **Artifact gate (blocking)**
   - CI must publish metrics JSON, confusion matrix, FAR/FRR report, latency histogram, and run metadata.

## Sign-off checklist

Before tagging a v3 release candidate:
- Validation report references corpus version hash and benchmark configuration.
- All blocking gates pass on default hardware profile.
- Any approved waivers are listed with expiration release.
