# AURA Evaluation Methodology & Benchmark Protocol

## 1. Evaluation Philosophy

AURA's evaluation methodology is grounded in **strict state verification** rather than superficial command completion. A task is considered successful **if and only if** the post-action system state strictly satisfies the formal `ExpectedState` criteria.

---

## 2. Formal Metric Definitions

### 1. Task Success Rate ($S_{task}$)
The proportion of attempted tasks reaching verified expected final states:
$$S_{task} = \frac{N_{verified\_success}}{N_{total\_attempted}}$$

### 2. Verification Accuracy ($V_{acc}$)
The precision of AURA's internal StateComparator in validating whether execution reached the goal:
$$V_{acc} = \frac{N_{correct\_verifications}}{N_{total\_verifications}}$$

### 3. Target Grounding Accuracy ($G_{acc}$)
The rate at which natural language UI targets are matched to the correct visual element:
$$G_{acc} = \frac{N_{correct\_grounding}}{N_{grounding\_queries}}$$

### 4. Recovery Success Rate ($R_{rec}$)
The effectiveness of the 10-tier RecoveryEngine when encountering recoverable runtime faults:
$$R_{rec} = \frac{N_{recovered\_successes}}{N_{recoverable\_failures}}$$

### 5. Replanning Rate ($R_{plan}$)
The frequency with which the DAG replanner restructured task execution at runtime:
$$R_{plan} = \frac{N_{replanned\_tasks}}{N_{total\_tasks}}$$

### 6. Tutoring Completion Rate ($T_{comp}$)
The percentage of tutoring workflows where the user completed the action and AURA verified state changes:
$$T_{comp} = \frac{N_{verified\_tutoring\_steps}}{N_{total\_tutoring\_steps}}$$

### 7. Content Extraction & QA Grounding Rates
- **Extraction Rate ($C_{ext}$)**: Proportion of supported document types successfully parsed into structured `ContentDocument` models.
- **QA Grounding Rate ($Q_{ground}$)**: Proportion of answered questions substantiated with exact structural citations (`page`, `slide`, `sheet!cell`, `dom`).

---

## 3. Evaluation Categories & Scenarios

| Category | Identifier | Description | Key Verification Metric |
|---|---|---|---|
| **Desktop** | `SC-DSK-01`, `SC-DSK-02` | App launch, window focus, typing | Process state, window hierarchy |
| **Browser** | `SC-BRW-01`, `SC-BRW-02` | Navigation, web extraction, forms | URL verification, DOM presence |
| **Filesystem** | `SC-FS-01`, `SC-FS-02` | Folder creation, file search, copy | File system existence, path integrity |
| **Perception** | `SC-PRC-01`, `SC-PRC-02` | Visual grounding, spatial & ordinal reasoning | Element ID match, bounding box intersection |
| **Agent** | `SC-AGT-01`, `SC-AGT-02` | Multi-step DAG, context resolution, cancellation | DAG completion, state cancellation |
| **Content** | `SC-CNT-01` to `SC-CNT-03` | PDF summarization, XLSX analytics, PPTX creation | Document model integrity, numerical accuracy |
| **Tutoring** | `SC-TUT-01` | Step instruction, WAITING_FOR_USER, user action verification | Observation diff detection |

---

## 4. Reproducing Evaluation Benchmarks

To execute the standardized benchmark suite and generate machine-readable JSON reports:

```powershell
# Run benchmark runner
python -m app.evaluation.benchmark_runner
```

Benchmark output reports are saved with full execution traces in `data/evaluation/eval_run_<RUN_ID>.json`.
