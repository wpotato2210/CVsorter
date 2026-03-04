# CV Parsing & Ranking Evaluation Dataset Specification

## 1) Dataset Overview (<=120 words)
Target **120 CVs** and **12 jobs** for the first benchmark release. This size is deliberately small enough for full manual quality control (double annotation + adjudication), yet large enough to expose ranking and parsing failures across document styles, language, and corruption levels. The dataset validates production behavior in three layers: (1) file ingestion robustness, (2) extraction correctness for skills/experience/education sections, and (3) ranking fidelity against human judgments (including ties and partial relevance). A clean-only corpus can inflate results; this mix is adversarial by design and reviewer-credible.

## 2) Repo Directory Layout

```text
/eval_dataset/
  /cvs/
    /raw/                      # Source CV files (pdf/docx/txt/image-PDF)
    /normalized_text/          # Optional parser text dumps for debugging regressions
  /jobs/                       # Job specs (JSON files)
  /ground_truth/
    /labels/                   # Per (job_id, cv_id) graded human labels
    /rankings/                 # Final adjudicated per-job rankings (ties allowed)
  /metadata/
    cv_manifest.json           # cv_id, format, language, pages, corruption tags
    job_manifest.json          # job_id, role family, seniority, required skill summary
    annotators.json            # annotator metadata and domain tags
  /failures/                   # Machine-generated JSONL failure logs from eval runs
  /runs/                       # Versioned evaluation outputs (metrics + config + model info)
  /scripts/
    run_eval.py
    validate_dataset.py
  README.md
```

## 3) CV Corpus Design (Total = 120)

| Category | Count | Why it matters | Typical failures exposed |
|---|---:|---|---|
| Clean single-column resumes | 30 | Baseline correctness; parser should be near-perfect | Unexpected regressions in basic extraction |
| Multi-column modern resumes | 24 | Common real-world layout with sidebars | Section bleed, chronology merge errors |
| Academic CVs (long-form) | 16 | Dense publication-heavy structure | Overweighting publications, date parsing drift |
| Table-heavy resumes | 14 | Frequent in exported corporate templates | Cell-order loss, role/company misalignment |
| Badly formatted PDFs | 16 | Upload noise mirrors production | OCR failures, broken encoding, parse crashes |
| Minimal resumes | 10 | Sparse signals test confidence handling | Overconfident ranking, false negatives |
| Non-English resumes | 10 | Multilingual robustness is high-signal | Language detect errors, skill synonym misses |

**Sum: 120 CVs**

## 4) Job Description Set

- **Job count:** 12
- **Role coverage:**
  - 3 engineering/data (Backend, Data Engineer, ML Engineer)
  - 2 product/program (PM, TPM)
  - 2 analytics/BI
  - 2 design/UX
  - 2 operations/support
  - 1 finance/business (FP&A)
- **Structure rule:** every job must have explicit `required_skills` and `preferred_skills`; hard constraints stay separate from nice-to-have constraints.

### Job Spec JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "JobSpec",
  "type": "object",
  "required": [
    "job_id",
    "title",
    "role_family",
    "seniority",
    "location_type",
    "required_experience_years",
    "required_skills",
    "preferred_skills",
    "description"
  ],
  "properties": {
    "job_id": { "type": "string" },
    "title": { "type": "string" },
    "role_family": { "type": "string" },
    "seniority": {
      "type": "string",
      "enum": ["junior", "mid", "senior", "staff"]
    },
    "location_type": {
      "type": "string",
      "enum": ["onsite", "hybrid", "remote"]
    },
    "required_experience_years": { "type": "number", "minimum": 0 },
    "required_skills": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1
    },
    "preferred_skills": {
      "type": "array",
      "items": { "type": "string" }
    },
    "must_have_constraints": {
      "type": "array",
      "items": { "type": "string" }
    },
    "nice_to_have_constraints": {
      "type": "array",
      "items": { "type": "string" }
    },
    "description": { "type": "string" }
  }
}
```

## 5) Ground Truth Ranking Design

Store labels and rankings separately.

### Per (job, CV) graded label schema

```json
{
  "job_id": "J001",
  "cv_id": "CV078",
  "relevance_grade": 3,
  "label_type": "human",
  "rationale_tags": ["required_skill_match", "experience_match"],
  "confidence": "high",
  "annotator_ids": ["A02", "A11"],
  "adjudicated": true
}
```

- `relevance_grade`: `0=irrelevant, 1=weak, 2=partial, 3=strong, 4=excellent`
- `confidence`: `low|medium|high`

### Adjudicated ranking schema (ties + agreement)

```json
{
  "job_id": "J001",
  "ranking": [
    { "rank": 1, "cv_ids": ["CV011", "CV044"] },
    { "rank": 2, "cv_ids": ["CV078"] },
    { "rank": 3, "cv_ids": ["CV032", "CV099"] }
  ],
  "graded_labels_reference": "ground_truth/labels/J001_labels.json",
  "agreement": {
    "metric": "krippendorff_alpha",
    "value": 0.74,
    "n_annotators": 2
  }
}
```

## 6) Evaluation Metrics

Compute per job, then macro-average across jobs.

1. **Rank correlation (Spearman rho)**
   - Tie-adjusted implementation.
   - No-tie form: `rho = 1 - 6*sum(d_i^2)/(n*(n^2-1))`
   - Why: global ordering alignment with human ranking.

2. **Precision@k**
   - `P@k = (# relevant in top-k) / k`
   - Relevant threshold: `relevance_grade >= 3`
   - Why: short-list quality.

3. **Recall@k**
   - `Recall@k = (# relevant in top-k) / (# all relevant)`
   - Why: measures missed qualified candidates.

4. **Parsing Success Rate**
   - `PSR = (# CVs parsed with required fields) / (# CVs processed)`
   - Required fields: candidate identifier, skills section, experience section.
   - Why: ranking metrics are invalid if ingestion fails.

## 7) Failure Mode Tracking (JSON schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EvalFailureLog",
  "type": "object",
  "required": [
    "run_id",
    "job_id",
    "cv_id",
    "stage",
    "failure_type",
    "severity",
    "timestamp"
  ],
  "properties": {
    "run_id": { "type": "string" },
    "job_id": { "type": "string" },
    "cv_id": { "type": "string" },
    "stage": { "type": "string", "enum": ["parse", "rank", "eval"] },
    "failure_type": {
      "type": "string",
      "enum": [
        "parsing_failure",
        "low_confidence_extraction",
        "malformed_file",
        "section_detection_error",
        "ranking_anomaly"
      ]
    },
    "severity": { "type": "string", "enum": ["low", "medium", "high", "critical"] },
    "details": { "type": "object" },
    "file_metadata": {
      "type": "object",
      "properties": {
        "format": { "type": "string" },
        "language": { "type": "string" },
        "ocr_used": { "type": "boolean" },
        "page_count": { "type": "integer", "minimum": 1 }
      }
    },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```

## 8) `run_eval.py` Reproducible Workflow

1. Parse CLI args and load run config.
2. Validate dataset files against JSON schemas (`validate_dataset.py`).
3. Load CV and job manifests; assert ID consistency.
4. Parse CVs into structured candidate profiles.
5. Persist parse outputs and parser confidence scores.
6. Score all parsed candidates against each job.
7. Produce per-job ranking (stable sorting + tie groups).
8. Compare predictions to ground truth labels/rankings.
9. Compute metrics: Spearman rho, P@k, Recall@k, Parsing Success Rate.
10. Emit failure logs (`/failures/*.jsonl`) for parse/rank issues.
11. Write run artifact bundle under `/runs/<timestamp>/` with config, metrics, and model/version metadata.
12. Exit non-zero on schema failure or minimum coverage violation.

### CLI example

```bash
python eval_dataset/scripts/run_eval.py \
  --dataset-root eval_dataset \
  --output-dir eval_dataset/runs/2026-03-04T12-00-00Z \
  --k-values 5 10 \
  --relevance-threshold 3 \
  --min-parser-confidence 0.60 \
  --min-job-coverage 0.80
```

## 9) Minimum Viable Dataset (2-week build)

- **CVs:** 48
  - clean 12, multi-column 10, academic 6, table-heavy 6, malformed 8, minimal 4, non-English 2
- **Jobs:** 6
  - Backend Engineer, Data Analyst, Product Manager, UX Designer, Ops Analyst, FP&A Analyst

Why credible in 2 weeks: enough heterogeneity for visible failure analysis, feasible for dual annotation + adjudication, and sufficient to compute stable macro P@k/Recall@k/rank-correlation trends.

## 10) Stretch Version (Production-grade)

- **Target scale:** 1,000 CVs, 80 jobs, 8+ languages, multi-industry.
- **Automation:** CI schema validation, nightly deterministic evaluation, metric drift alerts, run metadata pinning (model hash + parser build).
- **Synthetic augmentation:** controlled layout perturbations, OCR noise injection, skill-synonym rewrites, chronology shuffling, encoding corruption.
- **Continuous evaluation:**
  - Frozen gold benchmark + rotating challenge set.
  - Release gate thresholds (e.g., `PSR >= 95%`, `P@10` non-regression > -2%).
  - Failure-mode SLAs: recurring failure classes must map to tracked fixes and targeted re-tests.
