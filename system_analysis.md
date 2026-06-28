# System Analysis

## Executive Summary

This repository contains two overlapping architectures:

1. An active security monitoring and deception stack centered around `agents/`, `core/`, `collectors/`, `detectors/`, `logs/`, and `ml/`.
2. An older `src/` inference pipeline scaffold that is mostly placeholder code and is not the dominant runtime path.

The dominant executable path in code is:

`main.py` -> `agents.system_agent.SystemAgent.start()` -> `core.monitor.Monitor.collect()` -> `agents.event_enrichment.EventEnricher.enrich()` -> `utils.filters.EventFilter` -> `detectors.scoring.ScoringDetector.analyze()` -> `logs.logger.SOCLogger.emit()` -> ML routing/aggregation -> LLM-driven `analysis` -> `strategy` -> decoy `deployment` -> optional `interception` / `generation`.

## Dominant Workflow Inferred From Code

### 1. Monitoring / Detection Flow

1. `SystemAgent.start()` loops forever.
2. `Monitor.collect()` merges process, file, and network events from the three collectors.
3. `EventEnricher` mutates each event in place and adds ML features such as z-scores, rarity, known-binary flags, IP features, and file frequency.
4. `EventFilter.should_ignore_noise()` removes trusted/local/noisy events.
5. `ScoringDetector.analyze()` applies rule-based scoring by event type.
6. `EventFilter.apply_known_process_logic()` suppresses low-score trusted process events.
7. `SOCLogger.emit()` transforms suspicious events into ML payloads, routes them into the corresponding model, and sends the model output into `StreamingAggregator`.
8. When the streaming aggregate crosses threshold, the aggregated risk/events become input for the deception decision flow.

### 2. Deception Planning Flow

1. `agents.analysis.analysis_agent.analysis_agent()` turns aggregated suspicious events into `{intent, attack_stage, confidence, reasoning}` using an LLM.
2. `agents.strategy.strategy_agent.strategy_agent()` converts analysis into a structured deception plan with placement rules, artifact counts, monitoring rules, and safety controls.
3. `agents.deployment.deployment_agent.DeploymentManager.deploy()` turns the strategy into a decoy registry, organization context, and interception rules.

### 3. Interception / Decoy Response Flow

1. `core.interception_layer.InterceptionLayer.handle()` receives a file access request plus analysis and deployment state.
2. It normalizes the requested path and checks whether a decoy entry exists.
3. `core.decision_engine.decide_action()` decides `real`, `partial`, or `fake` based on confidence, stage, intent, supported file type, and per-path rule mode.
4. For fake or partial responses, `agents.generation.generation_agent.GenerationAgent.generate()` creates or reuses believable decoy content.
5. Generated content is cached and written into the decoy filesystem under `decoy_env/`.

## Ambiguities And Resolution

- `src/inference/*` and `src/aggregation/*` define an older pipeline but every major function is `pass`. I treated these as legacy scaffolding, not the active runtime.
- `agents/deception_graph.py` contains an earlier LangGraph prototype for `analysis -> strategy -> generation`, but it is incomplete and does not cover monitoring, deployment, or interception.
- Tests and debug scripts indicate the intended end-to-end architecture combines live monitoring with deception generation, even though the original runtime only executed the monitoring half directly.
- The ML router referenced relative imports and a missing network model artifact. I treated ML inference as best-effort and preserved runtime via safe fallbacks instead of deleting the path.

## Unified Interpretation

- `collectors/` are event sources.
- `agents/event_enrichment.py` is a feature engineering processor for runtime events.
- `detectors/scoring.py` is a first-pass heuristic detector.
- `logs/logger.py` is a pipeline/orchestrator boundary that turns heuristic detections into ML model inputs and aggregation state.
- `ml/ml_models/*` are predictive models.
- `agents/analysis`, `agents/strategy`, and parts of `utils/llm_client.py` are LLM agents.
- `agents/deployment` and `core/interception_layer.py` are coordination/orchestration logic.
- `agents/generation/*` is the decoy artifact generation processor stack.

## Component Inventory

### Entry Points

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `main.py` | entry point | Starts the system agent runtime | YAML config files | long-running process | `yaml`, `agents.system_agent` | reads config, prints startup info |
| `agents/main.py` | entry point | Alternate launcher for `SystemAgent` | none | long-running process | `agents.system_agent` | starts monitor loop |
| `tests/run_event_pipeline.py` | demo pipeline | Demonstrates deployment + interception on file events | mock strategy/analysis, filesystem events | console output | deployment, interception, generation, file collector | watches filesystem, prints output |
| `debug_stratergy_agent.py` | debug harness | Runs strategy agent with multiple inputs | mocked analysis states | console output | strategy agent | loads env, prints JSON |
| `debug_2_stratergy.py` | debug harness | Runs one strategy case and validates shape | mocked analysis state | console output | strategy agent/schema | loads env, prints JSON |

### Monitoring / Event Collection

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `agents/system_agent.py` | pipeline runner | Executes the monitoring graph in a loop | persisted graph state | updated graph state | `langgraph_pipeline` | long-running loop |
| `core/monitor.py` | pipeline | Collects all event streams | collector instances | list of events | process/file/network collectors | none directly |
| `collectors/process_collector.py` | collector | Samples live processes and emits process events | process table | process event dicts | `psutil`, `time` | reads process metadata, sleeps |
| `collectors/file_collector.py` | collector | Buffers filesystem create/modify/delete events | watch path | file access events | `watchdog`, `threading`, `os` | starts observer thread |
| `collectors/network_collector.py` | collector | Reads current inet connections | system network connections | network event dicts | `psutil`, `time` | reads live socket table |

### Runtime Feature Engineering / Filtering / Detection

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `agents/event_enrichment.py` | processor | Adds runtime ML features to events | raw event dicts | enriched event dicts | `psutil`, `statistics`, `ipaddress`, `os` | reads process state, mutates events |
| `utils/filters.py` | processor | Drops trusted/local noise and suppresses trusted low-risk processes | event + detection | bool decisions | `ipaddress` | mutates `is_known` flag |
| `detectors/scoring.py` | detector | Rule-based suspiciousness scoring | enriched events | `{score, severity, reasons}` | `re`, `time`, `ipaddress` | maintains recent file activity deques |

### ML Routing / Alert Aggregation

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `logs/logger.py` | pipeline | Converts detections to ML payloads, runs model router, aggregates stream risk | event + detection | model + aggregation output | router, streaming aggregator | rate-limiting state, prints JSON |
| `ml/pipeline_runner.py` | demo pipeline | Manual ML routing/aggregation runner | synthetic events | aggregation output | model router, aggregator | prints results |
| `ml/ml_models/aggregator_model/router.py` | router | Selects file/network/process model | ML payload | model prediction output | model classes | prints model load errors |
| `ml/ml_models/aggregator_model/aggregator.py` | pipeline | Streaming threshold aggregation with decay | model-scored event | alert/no-alert state | `time`, `copy` | stores event queue |
| `ml/ml_models/file_model/file_model.py` | ML model | Hybrid file anomaly predictor | file ML payload | risk score + summarized event | `pickle`, `pandas` | loads pickle model |
| `ml/ml_models/network_model/network_model.py` | ML model | Hybrid network anomaly predictor | network ML payload | risk score + summarized event | `pickle`, `pandas` | loads pickle model |
| `ml/ml_models/process_model/process_model.py` | ML model | Hybrid process anomaly predictor | process ML payload | risk score + summarized event | `pickle`, `pandas` | loads pickle model |
| `ml/ml_models/file_model/train.py` | training | File model training script | processed datasets | serialized model | ML libs | file I/O, model training |
| `ml/ml_models/network_model/train.py` | training | Network model training script | processed datasets | serialized model | ML libs | file I/O, model training |
| `ml/ml_models/process_model/train.py` | training | Process model training script | processed datasets | serialized model | ML libs | file I/O, model training |
| `ml/ml_models/file_model/test_file_model.py` | test/demo | File model tests | model + test data | assertions/output | model code | may read models |
| `ml/ml_models/process_model/test_process_hybrid_model.py` | test/demo | Process model tests | model + test data | assertions/output | model code | may read models |

### LLM Analysis / Strategy Agents

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `agents/analysis/analysis_agent.py` | agent | Produces attacker intent/stage analysis | `risk_score`, aggregated events | `analysis` dict | formatter, prompt builder, parser, validator, LLM client | remote LLM call |
| `agents/analysis/formatter.py` | processor | Formats event list into analysis prompt text | event list | string | none | none |
| `agents/analysis/prompt_builder.py` | processor | Builds analysis prompt | risk score + formatted events | string | none | none |
| `agents/analysis/parser.py` | processor | Parses LLM JSON-ish output | raw LLM text | normalized dict | `json`, `re`, `ast` | prints parse errors |
| `agents/analysis/validator.py` | processor | Validates intent/stage/confidence values | parsed dict | cleaned dict | none | none |
| `agents/strategy/strategy_agent.py` | agent | Converts analysis into executable deception plan | `analysis` dict | `strategy`, `strategy_meta` | prompt builder, parser, schema, validator, LLM client | remote OpenAI call, prints fallback info |
| `agents/strategy/prompt_builder.py` | processor | Builds deterministic hints and strategy prompt | analysis + staging path | strings | none | none |
| `agents/strategy/parser.py` | processor | Parses strategy agent JSON | raw LLM text | strategy dict | parsing utils | none |
| `agents/strategy/schema.py` | schema | Shared constants, TypedDicts, limit functions | analysis metadata | strategy constraints | typing | none |
| `agents/strategy/validator.py` | processor | Validates/sanitizes strategy plan and builds fallback | parsed strategy + analysis | validated strategy | schema helpers | none |
| `utils/llm_client.py` | utility | Shared Groq/OpenAI LLM clients | prompt + model params | text/JSON | `groq`, `openai`, `dotenv` | env reads, network calls, prints fallback/errors |

### Deployment / Interception

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `agents/deployment/deployment_agent.py` | pipeline | Builds decoy registry, context, and interception rules from strategy | strategy output | deployment state | decoy registry, context builder, rule engine, path resolver | may create placeholder files |
| `agents/deployment/decoy_registry.py` | utility | In-memory registry of decoy metadata | path + metadata | lookup dict | none | stores registry state |
| `agents/deployment/context_builder.py` | processor | Builds fake org-wide context | none | org context dict | `random`, `time` | random generation |
| `agents/deployment/rule_engine.py` | processor | Produces per-path interception rules | decoy registry | rule dict | none | none |
| `agents/deployment/models.py` | schema | Dataclasses for deployment payloads | Python objects | typed records | `dataclasses` | none |
| `core/interception_layer.py` | pipeline | Decides real/partial/fake response for file access | path + analysis + deployment | intercepted content | decision engine, path resolver, generation agent | reads real files, may generate decoys |
| `core/decision_engine.py` | processor | Rule logic for `real` vs `partial` vs `fake` | path metadata rules analysis | action string | none | none |
| `core/path_resolver.py` | utility | Maps virtual paths to `decoy_env/` | external path string | normalized/real decoy path | `os` | none |
| `core/context_builder.py` | processor | Builds interception request payload from event + analysis + deployment | event + analysis + deployment | dict | none | none |

### Decoy Content Generation

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `agents/generation/generation_agent.py` | pipeline | Orchestrates schema resolution, fake content generation, validation, caching, and decoy writes | path + metadata | generation result dict | cache, schema resolver, data generator, consistency, realism, validators, path resolver | cache writes, decoy file writes |
| `agents/generation/schema_resolver.py` | processor | Resolves likely file schema deterministically then via LLM fallback | path + metadata | schema list | LLM client, `os`, `random` | optional remote LLM call |
| `agents/generation/data_generator.py` | processor | Generates fake CSV/JSON/SQL/log/txt/env content | path + metadata + schema | content string | `random`, `json`, `csv`, `datetime`, `os` | prints debug lines |
| `agents/generation/consistency_engine.py` | processor | Normalizes people/org identities across generated content | content + metadata | adjusted content | `json`, `csv`, `re`, `random` | in-memory global profile state |
| `agents/generation/realism_enhancer.py` | processor | Adds realistic imperfections and optional LLM polish | content + metadata | adjusted content | `random`, `json`, `re`, LLM client | optional remote LLM call |
| `agents/generation/validators.py` | processor | Validates metadata and generated artifacts | content + metadata + schema | `(bool, reason)` | `json`, `re` | none |
| `agents/generation/cache.py` | utility | Cache for generated fake files keyed by path+metadata | path + content metadata | cached payloads | `os`, `json`, `hashlib` | disk writes in `cache/generated_files` |

### LangGraph Orchestration

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `state_schema.py` | schema | Shared graph state definition | graph state values | TypedDict contracts | typing | none |
| `langgraph_pipeline.py` | pipeline | LangGraph orchestration over monitoring, analysis, strategy, deployment, interception | optional events/path/prior state | updated shared state | LangGraph + existing runtime components | may trigger all existing side effects via wrapped nodes |
| `agents/deception_graph.py` | prototype pipeline | Earlier LangGraph sketch for `analysis -> strategy -> generation` | risk score + events | partial workflow state | analysis, strategy, generation agents | none directly |

### Legacy / Placeholder `src/` Stack

| File | Type | Purpose | Inputs | Outputs | Dependencies | Side Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `src/inference/pipeline.py` | legacy pipeline | Placeholder orchestrator | event | none yet | none | none |
| `src/inference/router.py` | legacy router | Placeholder event router | event | none yet | none | none |
| `src/inference/handlers.py` | legacy handlers | Placeholder per-event handlers | event | none yet | none | none |
| `src/aggregation/aggregator.py` | legacy pipeline | Placeholder prediction aggregation | predictions | none yet | none | none |
| `src/aggregation/correlation.py` | legacy processor | Placeholder anomaly correlation | events | none yet | none | none |
| `src/aggregation/time_bucketing.py` | legacy processor | Placeholder time bucketing | events + bucket size | none yet | none | none |
| `src/data_processing/loader.py` | data utility | Dataset loading/prep support | dataset files | dataframes/data | pandas/sklearn utilities | file I/O |
| `src/data_processing/split_dataset.py` | data utility | Dataset split utility | datasets | train/test sets | pandas/sklearn | file I/O |
| `src/feature_engineering/process_features.py` | processor | Process feature engineering for offline training | process dataset | engineered features | pandas/numpy | file I/O |
| `src/feature_engineering/file_features.py` | processor | File feature engineering for offline training | file dataset | engineered features | pandas/numpy | file I/O |
| `src/feature_engineering/network_features.py` | processor | Network feature engineering for offline training | network dataset | engineered features | pandas/numpy | file I/O |
| `src/utils/encoding.py` | utility | Encoding helpers for offline pipeline | datasets | transformed data | pandas/sklearn | none/file I/O |
| `src/utils/helpers.py` | utility | General data helpers | datasets | helper outputs | none | none |
| `src/utils/preprocessing.py` | utility | Preprocessing helpers | datasets | transformed data | pandas/sklearn | none |

### Package Markers / Thin Modules

- `agents/__init__.py`
- `agents/analysis/__init__.py`
- `agents/deployment/__init__.py`
- `agents/generation/__init__.py`
- `agents/strategy/__init__.py`
- `collectors/__init__` is absent
- `config/__init__.py`
- `core/__init__.py`
- `detectors/__init__.py`
- `ml/__init__.py`
- `ml/ml_models/__init__.py`
- `ml/ml_models/file_model/__init__.py`
- `ml/ml_models/network_model/__init__.py`
- `ml/ml_models/process_model/__init__.py`
- `ml/ml_models/aggregator_model/__init__.py`
- `utils/__init__.py`

These exist only to define packages and do not materially affect runtime behavior.

## Global Shared State Design

The LangGraph refactor uses a single extensible shared state:

- `mode`: `monitor` or `intercept`
- `input_events`: optional externally supplied events
- `raw_events`: collected telemetry
- `enriched_events`: telemetry after feature enrichment
- `filtered_events`: telemetry after noise suppression
- `detections`: event + detection + acceptance records
- `suspicious_events`: accepted suspicious events
- `alert_records`: logger/router/aggregator outputs
- `risk_score`: dominant aggregated risk score
- `analysis`: LLM attacker interpretation
- `strategy`: deception strategy plan
- `strategy_meta`: provenance/fallback metadata from strategy generation
- `deployment`: decoy registry + rules + fake org context
- `request_path`: optional file path for interception mode
- `interception_result`: final real/partial/fake content returned to caller
- `errors`: non-fatal pipeline issues
- `notes`: operational trace notes

## Assumptions Made During Refactor

- The active runtime should prioritize the `agents/` and `core/` stack over the placeholder `src/` stack.
- The heuristic detector is intentionally permissive because the ML router/aggregator is meant to be the second-stage signal combiner.
- Strategy/deployment should only run when the streaming aggregator actually raises an alert, not for every suspicious single event.
- Interception is a separate operational mode that consumes previously produced `analysis` and `deployment` state.
- Missing model artifacts should not crash the runtime; they should degrade to safe fallback behavior.

## Minimal Integration Changes Applied

- Replaced the ad hoc `SystemAgent` loop with a LangGraph-backed orchestration loop.
- Updated `main.py` to launch the integrated system agent instead of the unused stub pipeline.
- Added `state_schema.py` and `langgraph_pipeline.py`.
- Fixed router imports/model-path handling so the ML stage can run from the repository root.
- Fixed deployment metadata so rule generation receives `sensitivity` and `realism`.
- Fixed interception real-file reads so reason-tagged responses are preserved.
- Fixed streaming aggregation to stop duplicating queued events.

