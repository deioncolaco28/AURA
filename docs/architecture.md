# AURA System Architecture Specification

## 1. High-Level System Architecture

```mermaid
flowchart TD
    User([User Voice / Text]) --> Ingestion[Voice STT / Text Ingestion]
    Ingestion --> Intent[Intent Parser & Mode Router]
    
    Intent -->|DO_IT_FOR_ME| Planner[Task Planner & DAG Generator]
    Intent -->|SHOW_ME_HOW| Tutor[Tutoring Controller]
    
    Planner --> Graph[TaskGraph / ExecutionEngine]
    
    Graph --> SelectEnv[Environment Registry]
    SelectEnv --> DskEnv[Desktop Environment]
    SelectEnv --> BrwEnv[Browser Environment]
    SelectEnv --> FsEnv[Filesystem Environment]
    SelectEnv --> CntEnv[Content Environment]
    
    DskEnv & BrwEnv & FsEnv & CntEnv --> ObservePre[Pre-Action Observation]
    ObservePre --> Grounding[Target Grounding & Safety Assessment]
    Grounding --> Exec[Action Executor]
    
    Exec --> ObservePost[Post-Action Observation]
    ObservePost --> Diff[Observation Diff & State Comparator]
    
    Diff -->|Success| Complete[Complete Node / Advance DAG]
    Diff -->|Failure| Classify[Failure Classifier]
    
    Classify --> Recovery[10-Tier Recovery Engine]
    Recovery -->|Replan / Retry| Graph
    Recovery -->|Unrecoverable| SafeFail[Safe Failure / Ask User]
```

---

## 2. Agent Execution Loop

The execution engine coordinates an observe-act-verify-recover cycle:

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant O as ScreenObserver
    participant S as SafetyManager
    participant A as ActionExecutor
    participant V as StateComparator
    participant R as RecoveryEngine

    E->>O: Observe Pre-State (DOM, OCR, Windows)
    E->>S: Assess Risk & Grounded Confidence
    alt Safe & Confident
        E->>A: Execute Action
        E->>O: Observe Post-State
        E->>V: Compare Expected State vs Actual Diff
        alt Verified
            V-->>E: Verification Success
        else Verification Failed
            V-->>E: Verification Error
            E->>R: Classify & Formulate Recovery Plan
            R-->>E: Bounded Recovery Strategy
        end
    else Confirmation Required
        S-->>E: Prompt User for Confirmation
    end
```

---

## 3. Computer Perception & Target Grounding Pipeline

```mermaid
flowchart LR
    Screen[Screen Frame / DOM] --> OCR[Tesseract OCR Engine]
    Screen --> DOM[Accessibility / UI Automation Tree]
    Screen --> VLM[Vision-Language Model Fallback]
    
    OCR & DOM & VLM --> Fusion[Perception Fusion & Identity Matcher]
    Fusion --> Graph[UIElementGraph]
    
    Query[Natural Language Query] --> Matcher[Spatial & Ordinal Reasoner]
    Graph --> Matcher
    Matcher --> RankedTarget[Ranked Target with Provenance & Confidence]
```

---

## 4. Content Intelligence Architecture

```mermaid
flowchart TD
    DocSource[Source File / Webpage] --> Manager[ContentManager]
    
    Manager --> PDF[PDF Adapter (pypdf + OCR)]
    Manager --> DOCX[DOCX Adapter (python-docx)]
    Manager --> XLSX[XLSX Adapter (openpyxl)]
    Manager --> PPTX[PPTX Adapter (python-pptx)]
    Manager --> Web[Web Adapter (beautifulsoup4)]
    
    PDF & DOCX & XLSX & PPTX & Web --> UnifiedDoc[Unified ContentDocument Model]
    
    UnifiedDoc --> Search[Coordinate Search & Provenance Index]
    UnifiedDoc --> Summarizer[Extractive Summarizer]
    UnifiedDoc --> QA[Grounded Q&A Engine]
    
    Summarizer --> Export[Multi-Format Exporter (DOCX, XLSX, PPTX)]
```

---

## 5. 10-Tier Deterministic Recovery Hierarchy

1. **`REOBSERVE`**: Recapture immediate screen state after modal dismiss or transient paint latency.
2. **`REGROUND`**: Recompute element spatial bounding boxes and visual hashes.
3. **`FOCUS_APPLICATION`**: Force window to foreground via Win32 API.
4. **`RETRY`**: Re-attempt action with minor spatial jitter or timing delay.
5. **`ALTERNATE_STRATEGY`**: Switch execution mechanism (e.g. Accessibility click $\rightarrow$ Keyboard Hotkey).
6. **`SCROLL_SEARCH`**: Perform directional scrolling to bring off-screen elements into view.
7. **`LOCAL_REPLAN`**: Replace failed step with equivalent multi-action sub-graph.
8. **`GLOBAL_REPLAN`**: Restructure remaining task graph dependencies.
9. **`ASK_USER`**: Prompt user for clarifying input when ambiguity is unresolved.
10. **`FAIL_SAFELY`**: Abort cleanly, preserve task traces, and restore desktop state.
