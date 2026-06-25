# Agentic Security System

LangGraph-orchestrated host monitoring and deception pipeline for process, file, and network telemetry.

This project combines:
- live telemetry collection
- rule-based detection
- ML routing and risk aggregation
- LLM-based attacker analysis
- LLM-based deception strategy planning
- dynamic file swapping and OS-level active defense
- **Real-time web dashboard for visualization**

The current runtime is centered around [main.py](main.py), [agents/system_agent.py](agents/system_agent.py), and [langgraph_pipeline.py](langgraph_pipeline.py).

## Overview

At a high level, the system works like this:

1. Collect process, file, and network events from the host.
2. Enrich those events with behavioral and ML-friendly features.
3. Filter known-noise telemetry.
4. Score suspicious activity with rule-based logic.
5. Route suspicious events into file/process/network ML models.
6. Aggregate model outputs into a global incident risk score.
7. If the risk is high enough, analyze likely attacker intent and attack stage.
8. Convert that analysis into a structured deception strategy.
9. Dynamically generate context-aware fake data matching the attacker's intent.
10. Execute **Dynamic File Swapping**: vault real files using NTFS cloaking and physically drop fake files in their place.

## Architecture

The active architecture is the `agents/`, `core/`, `collectors/`, `detectors/`, `logs/`, and `ml/` stack. 

### Main runtime path

`main.py -> SystemAgent -> LangGraphSecurityPipeline -> monitor -> enrich -> filter -> score -> ML aggregate -> analysis -> strategy -> deployment`

### Core orchestration files

- [langgraph_pipeline.py](langgraph_pipeline.py): full LangGraph workflow
- [state_schema.py](state_schema.py): shared graph state schema
- [agents/system_agent.py](agents/system_agent.py): long-running runtime loop

## LangGraph Workflow

The system is orchestrated as a `StateGraph(SecuritySystemState)` with these nodes:

- `prepare_state`
- `collect_events`
- `enrich_events`
- `filter_events`
- `score_events`
- `emit_alerts`
- `analysis`
- `strategy`
- `deployment`

### Shared state

The graph passes a single shared state object across all nodes, including:

- `mode`
- `input_events`
- `raw_events`
- `enriched_events`
- `filtered_events`
- `detections`
- `suspicious_events`
- `alert_records`
- `risk_score`
- `analysis`
- `strategy`
- `strategy_meta`
- `deployment`
- `request_path`
- `errors`
- `notes`
- `cycle_report`

### Routing behavior

- In `monitor` mode, the graph runs the full telemetry-to-response pipeline.
- After alert aggregation, the graph only continues to `analysis` if an aggregated alert is raised.
- After `strategy`, the graph only continues if a valid strategy exists.

## Repository Structure

### Runtime and orchestration

- [main.py](main.py): application entry point
- [langgraph_pipeline.py](langgraph_pipeline.py): LangGraph orchestration layer
- [state_schema.py](state_schema.py): graph state contract
- [agents/system_agent.py](agents/system_agent.py): runtime loop and live reporting

### Event collection

- [collectors/process_collector.py](collectors/process_collector.py): process telemetry
- [collectors/file_collector.py](collectors/file_collector.py): filesystem event monitoring
- [collectors/network_collector.py](collectors/network_collector.py): network connection telemetry
- [core/monitor.py](core/monitor.py): combines all collectors

### Detection and ML

- [agents/event_enrichment.py](agents/event_enrichment.py): feature enrichment
- [utils/filters.py](utils/filters.py): noise reduction and trusted-process suppression
- [detectors/scoring.py](detectors/scoring.py): heuristic scoring detector
- [logs/logger.py](logs/logger.py): ML payload creation and aggregation boundary
- [ml/ml_models/aggregator_model/router.py](ml/ml_models/aggregator_model/router.py): model routing
- [ml/ml_models/aggregator_model/aggregator.py](ml/ml_models/aggregator_model/aggregator.py): streaming alert aggregation

### LLM agents

- [agents/analysis/analysis_agent.py](agents/analysis/analysis_agent.py): attacker intent/stage analysis
- [agents/strategy/strategy_agent.py](agents/strategy/strategy_agent.py): deception planning
- [utils/llm_client.py](utils/llm_client.py): shared LLM client

### Deception and response

- [agents/deployment/deployment_agent.py](agents/deployment/deployment_agent.py): automated vaulting and decoy deployment
- [agents/generation/generation_agent.py](agents/generation/generation_agent.py): fake file content generation
- [test_swap.py](test_swap.py): testing utility for active defense (swapping & recovery)

### Frontend and Visualization

- [dashboard_server.py](dashboard_server.py): API backend for serving telemetry and dashboard metrics
- `frontend/`: React/Node.js based visualization UI for observing the system in real-time

## Requirements

### Python

- Python `>=3.13`

### Node.js (For Frontend)

- Node.js & npm (latest LTS recommended)

### Models

These model artifacts must exist:

- `ml/ml_models/file_model/file_hybrid_final.pkl`
- `ml/ml_models/process_model/process_hybrid_final.pkl`
- `ml/ml_models/network_model/network_hybrid_model.pkl`

### Environment variables

Create a `.env` file in the repo root with at least:

```env
OPENAI_API_KEY=your_key_here
```

## Installation

### Using the existing virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Fresh install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Building the Frontend

Before starting the dashboard server, you must compile the frontend:

```powershell
cd frontend
npm install
npm run build
cd ..
```

## Configuration

Primary runtime configuration lives in [configs/system_config.yaml](configs/system_config.yaml).

The `monitoring` section controls live file-watch behavior:

```yaml
monitoring:
  poll_interval: 1
  recursive: true
  console_reporting: true
  file_watch_paths:
    - ${USERPROFILE}\Documents
    - ${USERPROFILE}\Desktop
    - .\demo_shared
```

Use this to point the app at the folders you want to monitor on your machine.

## Running the system

### Start the live runtime (Terminal only)

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

### Start the Interactive Dashboard Server (UI)

If you want to view the system via the Web UI instead of the terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python dashboard_server.py
```
Once running, open your web browser and navigate to: `http://127.0.0.1:8765/`

### Test the Dynamic Active Defense (Swapping)

```powershell
python test_swap.py
```
This tests the full generation, vaulting, NTFS cloaking, and automated recovery workflow.

## Example end-to-end flow

Here is the dominant operational path:

1. Process/file/network collectors ingest telemetry.
2. Event enrichment adds features such as z-scores, rarity, trust, and frequency.
3. Filtering removes low-value noise.
4. Rule-based scoring classifies suspiciousness.
5. The logger transforms accepted detections into ML payloads.
6. File/process/network models score the events.
7. The streaming aggregator raises an alert when global risk crosses threshold.
8. The analysis agent infers intent and attack stage.
9. The strategy agent creates an executable decoy plan.
10. The deployment manager instantly vaults the genuine file using NTFS cloaking.
11. The generation agent dynamically synthesizes a realistic decoy.
12. The deployment manager physically deploys the decoy to trick the attacker at the OS level.

## Strategy agent summary

The strategy agent is the planning layer between attacker understanding and deception deployment.

It:
- takes `intent`, `attack_stage`, and `confidence`
- builds a strict JSON-only LLM prompt
- forces artifact generation under a safe staging root
- constrains output by deterministic limits
- validates and repairs the plan

## Notes and limitations

- **OS-Level Deception without Kernel Drivers**: This project utilizes Dynamic File Swapping to achieve OS-level deception. It does not require writing complex, system-destabilizing kernel-level minifilters. When a threat is detected, genuine files are physically migrated into hidden NTFS-cloaked vaults, and hyper-realistic generated decoys are dropped in their place.
- **Graceful Lock Handling**: If an authentic file is locked by a legitimate process, the system gracefully pivots to deploying adjacent decoys to lure the attacker rather than crashing.
- **Automated Recovery**: All deception operations are tracked in a secure transaction log. Upon incident resolution, the system automatically wipes decoys and un-cloaks genuine files, guaranteeing zero data loss.
