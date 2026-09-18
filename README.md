# AURA — Automated User Response Assistant

> **A Grounded, Observable, and Recoverable Whole-PC Computer-Use Assistant**  
> Major Project — Semester 1 Final Release (Phases 1–6)

---

## 1. Overview & Problem Statement

Modern GUI computer-use agents often suffer from three critical flaws:
1. **Blind Execution**: Acting without verifying actual state changes, resulting in false-positive completions.
2. **Brittle Grounding**: Relying purely on raw pixel coordinates or ungrounded generative predictions that break upon UI shifts.
3. **Black-Box Failure**: Failing silently when an unexpected modal, process latency, or file error occurs without structured recovery.

**AURA (Automated User Response Assistant)** is an agentic computer-use platform designed for Windows desktop, browser, filesystem, and multi-format document automation. AURA features closed-loop perception, deterministic state verification, hierarchical recovery, structured task tracing, and dual operating modes: **`DO_IT_FOR_ME`** (Autonomous Execution) and **`SHOW_ME_HOW`** (Interactive Step-by-Step Tutoring).

---

## 2. Core Operating Modes

```text
               ┌──────────────────────────────┐
               │         User Request         │
               └──────────────┬───────────────┘
                              │
                    Intent & Mode Router
                              │
               ┌──────────────┴───────────────┐
               ▼                              ▼
      [ DO_IT_FOR_ME ]                 [ SHOW_ME_HOW ]
  Autonomous Task Execution     Interactive Step Tutoring
  - TaskGraph / DAG Plan        - Natural Spoken Instruction
  - Closed-Loop Observe/Act     - WAITING_FOR_USER State
  - Post-Observation Diffs      - Non-Intrusive Guidance
  - Hierarchical Recovery       - Verified User Actions
```

1. **`DO_IT_FOR_ME` (Autonomous Mode)**: AURA autonomously plans, decomposes, executes, verifies, and recovers whole-PC workflows across applications, browsers, files, and documents.
2. **`SHOW_ME_HOW` (Tutoring Mode)**: AURA guides the user step-by-step using natural speech and visual overlays. Critically, AURA enters an explicit `WAITING_FOR_USER` state, observes the screen for state transitions, and verifies the user's action before progressing.

---

## 3. System Architecture & Intelligence Stack

```text
USER (Voice / Text)
  │
  ▼
INTENT PARSER & MODE ROUTER
  │
  ▼
TASK PLANNER / DAG DECOMPOSER
  │
  ▼
ENVIRONMENT SELECTION (Desktop | Browser | Filesystem | Content | System)
  │
  ▼
PRE-ACTION OBSERVATION (OCR + VLM + DOM + Process Tree)
  │
  ▼
TARGET RESOLUTION & SAFETY CHECK (Risk Level & Evidence Confidence)
  │
  ▼
EXECUTE ACTION / SPEAK INSTRUCTION
  │
  ▼
POST-ACTION OBSERVATION & OBSERVATION DIFF
  │
  ▼
EXPECTED STATE VERIFICATION
  ├── [PASSED] ──► ADVANCE TO NEXT NODE / COMPLETE
  │
  └── [FAILED] ──► CLASSIFY FAILURE
                     │
                     ▼
                 10-TIER DETERMINISTIC RECOVERY ENGINE
                     │
                     ▼
                 REPLAN / RETRY / ASK USER / FAIL SAFELY
```

---

## 4. Key Subsystems & Capabilities

### A. Computer Perception & UI Understanding (`app/perception/`)
- Canonical `UIElement` representation with deterministic visual hashing and spatial bounding.
- Perception fusion combining Accessibility DOM, Tesseract OCR, and VLM fallback.
- Spatial and ordinal reasoning (`"second submit button"`, `"left of search bar"`).
- Foreground application tracking and window state awareness.

### B. Whole-PC Automation (`app/automation/`)
- Unified `EnvironmentRegistry` orchestrating `DesktopEnvironment`, `BrowserEnvironment`, `FilesystemEnvironment`, and `ContentEnvironment`.
- Native Windows UI automation via accessibility trees, PyAutoGUI, keyboard shortcuts, and process lifecycles.
- Safe filesystem operations with directory guards and permission checks.

### C. Agent Intelligence & Recovery (`app/intelligence/`, `app/core/`)
- Task graphs (DAGs) with explicit dependencies, state preconditions, and conditional branches.
- Task-scoped `TaskContext` resolving dynamic variables (`$report`, `$summary`, `"it"`).
- `StateComparator` performing observation diff verification against `ExpectedState`.
- 10-tier bounded `RecoveryEngine`:
  1. `REOBSERVE` $\rightarrow$ 2. `REGROUND` $\rightarrow$ 3. `FOCUS_APPLICATION` $\rightarrow$ 4. `RETRY` $\rightarrow$ 5. `ALTERNATE_STRATEGY` $\rightarrow$ 6. `SCROLL_SEARCH` $\rightarrow$ 7. `LOCAL_REPLAN` $\rightarrow$ 8. `GLOBAL_REPLAN` $\rightarrow$ 9. `ASK_USER` $\rightarrow$ 10. `FAIL_SAFELY`.

### D. Content Intelligence (`app/content/`)
- Multi-format document adapters: **PDF** (`pypdf` + OCR), **DOCX** (`python-docx`), **XLSX** (`openpyxl`), **PPTX** (`python-pptx`), **Web/HTML** (`beautifulsoup4`).
- Grounded extraction with structural provenance (`page_number`, `slide_number`, `sheet!cell`, `dom_selector`).
- Extractive summarization and anti-hallucination grounded Q&A.
- Safe non-destructive document and spreadsheet generation.

### E. Safety, Observability & Productization (`app/security/`, `app/logging/`, `app/config/`)
- Evidence-grounded confidence scoring and multi-tier risk policy (`LOW`, `MEDIUM`, `HIGH`).
- Protected critical directory guards (`C:\Windows`, `C:\Program Files`).
- Passive document isolation (disallowing code/macro execution).
- Machine-readable structured `TaskTrace` and `ExecutionMetrics` logging.
- `HealthChecker` readiness check on startup with graceful shutdown handlers.

---

## 5. Evaluation Benchmark Framework (`app/evaluation/`)

AURA includes a research evaluation harness capable of deterministic evaluation across 7 categories:

```powershell
python -m app.evaluation.benchmark_runner
```

### Metrics Tracked
| Metric | Definition |
|---|---|
| **Task Success Rate** | Percentage of tasks reaching verified expected final state |
| **Verification Accuracy** | Correctness of state comparator assertions |
| **Target Grounding Accuracy** | Precision in resolving natural language target queries |
| **Recovery Success Rate** | Percentage of recoverable faults restored autonomously |
| **Average Attempts/Task** | Mean action attempts per task node |
| **Replanning Rate** | Percentage of tasks requiring runtime graph replanning |
| **Tutoring Completion Rate** | Rate of user-performed tutoring actions verified |
| **Content Extraction Rate** | Grounded extraction rate across document formats |
| **Content QA Grounding Rate** | Percentage of Q&A answers with verifiable provenance |

---

## 6. Installation & Quick Start

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10, 3.11, or 3.12
- Google Chrome (for browser automation)

### Setup
```powershell
# Clone the repository
git clone https://github.com/deioncolaco28/AURA.git
cd AURA

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running AURA
```powershell
python run.py
```

### Running Tests
```powershell
# Run complete test suite (393 passing tests)
pytest -q

# Run benchmark evaluation runner
python -m app.evaluation.benchmark_runner

# Verify syntax & compilation
python -m compileall app
```

---

## 7. Canonical Demo Scenarios

1. **Desktop Automation**: `"Open Notepad and type Hello AURA."`
2. **Browser Automation**: `"Open Chrome and go to Google."`
3. **Filesystem Automation**: `"Create a folder called AURA Demo in Documents."`
4. **Context & Multi-Step**: `"Open the report, summarize it, and save the summary as a Word document."`
5. **Spreadsheet Analytics**: `"Find the highest AQI value in this spreadsheet air_quality.xlsx."`
6. **Presentation Creation**: `"Turn this report into a presentation."`
7. **Web Content Extraction**: `"Read this webpage and summarize it."`
8. **Fault Recovery**: Simulates target occlusion $\rightarrow$ classifies failure $\rightarrow$ regrounds $\rightarrow$ succeeds.
9. **Interactive Tutoring**: `"Show me how to open Calculator."` $\rightarrow$ Instructs $\rightarrow$ Waits $\rightarrow$ Verifies.
10. **Graceful Cancellation**: During multi-step execution $\rightarrow$ `"Cancel"` $\rightarrow$ Safely aborts and cleans up.

---

## 8. Project Scope & Boundaries

### Included in Semester 1 (Phases 1–6)
- Centralized typed configuration and health readiness checks.
- Whole-PC computer perception, visual grounding, and spatial reasoning.
- Multi-environment automation (Desktop, Browser, Filesystem, Content).
- Closed-loop DAG execution, state verification, and hierarchical recovery.
- Multi-format document parsing, summarization, Q&A, and generation.
- Full research evaluation harness and deterministic benchmark suite.

### Out of Scope / Planned for Semester 2
- Reinforcement learning and self-improving policy updates.
- Long-term personal user memory and cross-session profiling.
- Adaptive user habit learning.
- Cloud-based marketplace and remote plugin distributions.

---

## 9. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
