import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Brain,
  ChevronRight,
  CircleDot,
  Code2,
  Database,
  FileWarning,
  Gauge,
  GitBranch,
  HardDrive,
  Network,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TerminalSquare,
  Workflow,
  Zap,
} from "lucide-react";
import { Background, Controls, MarkerType, ReactFlow } from "@xyflow/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const views = [
  { id: "overview", label: "Overview", icon: Gauge },
  { id: "live", label: "Live Ops", icon: Radar },
  { id: "workflow", label: "Attack Flow", icon: Workflow },
  { id: "deception", label: "Deception", icon: Target },
  { id: "models", label: "ML Health", icon: Brain },
  { id: "code", label: "Code Intel", icon: Code2 },
  { id: "risks", label: "Risk Review", icon: AlertTriangle },
];

const workflowLabels = {
  prepare_state: "Prepare",
  collect_events: "Telemetry",
  enrich_events: "Enrich",
  filter_events: "Filter",
  score_events: "Score",
  emit_alerts: "ML Aggregate",
  analysis: "AI Analysis",
  strategy: "Strategy",
  deployment: "Deploy",
  interception: "Intercept",
};

const API_BASE = import.meta.env.VITE_DASHBOARD_API_BASE ?? "http://127.0.0.1:8765";

async function fetchBackendState() {
  const response = await fetch(`${API_BASE}/api/state`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Backend state failed: ${response.status}`);
  return response.json();
}

async function runBackendCycle() {
  const response = await fetch(`${API_BASE}/api/cycle`, { method: "POST" });
  if (!response.ok) throw new Error(`Backend cycle failed: ${response.status}`);
  return response.json();
}

async function runInterception(path) {
  const response = await fetch(`${API_BASE}/api/intercept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error ?? `Interception failed: ${response.status}`);
  }
  return response.json();
}

function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [backendState, setBackendState] = useState(null);
  const [backendError, setBackendError] = useState(null);
  const [backendBusy, setBackendBusy] = useState(false);
  const [backendAction, setBackendAction] = useState("");
  const [lastBackendSync, setLastBackendSync] = useState(null);
  const [activeView, setActiveView] = useState("overview");
  const [query, setQuery] = useState("");
  const [loadError, setLoadError] = useState(null);
  const [interceptPath, setInterceptPath] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch("/project-snapshot.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`Snapshot load failed: ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!cancelled) setSnapshot(data);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchBackendState()
      .then((data) => {
        if (!cancelled) {
          setBackendState(data);
          setBackendError(null);
          setLastBackendSync(new Date().toLocaleTimeString());
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setBackendState(null);
          setBackendError(error instanceof Error ? error.message : String(error));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (backendBusy) return undefined;
    const timer = window.setInterval(() => {
      fetchBackendState()
        .then((data) => {
          setBackendState(data);
          setBackendError(null);
          setLastBackendSync(new Date().toLocaleTimeString());
        })
        .catch((error) => {
          setBackendError(error instanceof Error ? error.message : String(error));
        });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [backendBusy]);

  const refreshBackend = () => {
    setBackendBusy(true);
    setBackendAction("sync");
    fetchBackendState()
      .then((data) => {
        setBackendState(data);
        setBackendError(null);
        setLastBackendSync(new Date().toLocaleTimeString());
      })
      .catch((error) => {
        setBackendError(error instanceof Error ? error.message : String(error));
      })
      .finally(() => {
        setBackendBusy(false);
        setBackendAction("");
      });
  };

  const runCycle = () => {
    setBackendBusy(true);
    setBackendAction("cycle");
    runBackendCycle()
      .then((data) => {
        setBackendState(data);
        setBackendError(null);
        setLastBackendSync(new Date().toLocaleTimeString());
      })
      .catch((error) => setBackendError(error instanceof Error ? error.message : String(error)))
      .finally(() => {
        setBackendBusy(false);
        setBackendAction("");
      });
  };

  const runPathInterception = () => {
    const path = interceptPath || backendState?.deployment?.decoys?.[0]?.path || snapshot?.decoys?.[0]?.path;
    if (!path) return;
    setBackendBusy(true);
    setBackendAction("intercept");
    runInterception(path)
      .then((data) => {
        setBackendState(data);
        setBackendError(null);
        setLastBackendSync(new Date().toLocaleTimeString());
        setInterceptPath("");
      })
      .catch((error) => setBackendError(error instanceof Error ? error.message : String(error)))
      .finally(() => {
        setBackendBusy(false);
        setBackendAction("");
      });
  };

  const filteredModules = useMemo(() => {
    const modules = snapshot?.modules ?? [];
    if (!query.trim()) return modules;
    const needle = query.toLowerCase();
    return modules.filter((module) => JSON.stringify(module).toLowerCase().includes(needle));
  }, [query, snapshot]);

  const posture = derivePosture(snapshot, backendState);

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={22} />
          </div>
          <div>
            <div className="brand-title">AADS Console</div>
            <div className="brand-subtitle">Agentic deception system</div>
          </div>
        </div>

        <nav className="nav-list">
          {views.map((view) => {
            const Icon = view.icon;
            return (
              <button
                className={`nav-item ${activeView === view.id ? "is-active" : ""}`}
                key={view.id}
                onClick={() => setActiveView(view.id)}
                type="button"
              >
                <Icon size={17} />
                <span>{view.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="runtime-card">
          <div className="runtime-topline">
            <span>Runtime</span>
            <CircleDot size={14} />
          </div>
          <strong>{backendState ? "manual API connected" : snapshot?.runtime.mode ?? "snapshot"}</strong>
          <span>{backendState?.backend.entrypoint ?? snapshot?.runtime.entrypoint ?? "main.py"}</span>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <div className={`status-pill ${posture.tone}`}>
              <CircleDot size={15} />
              {posture.label}
            </div>
            <h1>Active Cyber Deception Console</h1>
            <p>{posture.summary}</p>
          </div>
          <div className="toolbar">
            <label className="search-box">
              <Search size={16} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search modules, decoys, risks" />
            </label>
            <button className="icon-button" type="button" onClick={() => window.location.reload()} title="Refresh snapshot">
              <RefreshCw size={17} />
            </button>
            <button className="command-button" type="button" onClick={refreshBackend} disabled={backendBusy}>
              {backendAction === "sync" ? "Syncing" : "Sync"}
            </button>
            <button className="command-button primary" type="button" onClick={runCycle} disabled={backendBusy}>
              {backendAction === "cycle" ? "Running" : "Run cycle"}
            </button>
          </div>
        </header>

        {loadError ? (
          <EmptyState title="Snapshot unavailable" detail={loadError} />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {activeView === "overview" && <Overview snapshot={snapshot} />}
              {activeView === "live" && (
                <LiveOps
                  backendState={backendState}
                  backendError={backendError}
                  backendBusy={backendBusy}
                  backendAction={backendAction}
                  lastBackendSync={lastBackendSync}
                  interceptPath={interceptPath}
                  setInterceptPath={setInterceptPath}
                  runCycle={runCycle}
                  refreshBackend={refreshBackend}
                  runPathInterception={runPathInterception}
                  snapshot={snapshot}
                />
              )}
              {activeView === "workflow" && <WorkflowView snapshot={snapshot} />}
              {activeView === "deception" && <DeceptionView snapshot={snapshot} />}
              {activeView === "models" && <ModelsView snapshot={snapshot} />}
              {activeView === "code" && <CodeIntel snapshot={snapshot} modules={filteredModules} />}
              {activeView === "risks" && <RisksView snapshot={snapshot} />}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
    </div>
  );
}

function Overview({ snapshot }) {
  const counts = snapshot?.counts;
  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={TerminalSquare} label="Python files" value={counts?.pythonFiles ?? 0} />
        <Metric icon={Workflow} label="Graph nodes" value={snapshot?.workflow.nodes.length ?? 0} />
        <Metric icon={Target} label="Decoys" value={snapshot?.decoys.length ?? 0} />
        <Metric icon={AlertTriangle} label="Findings" value={snapshot?.risks.length ?? 0} />
      </section>

      <section className="split-grid">
        <Panel title="Primary Execution Path" eyebrow="LangGraph">
          <StepList
            steps={[
              "Telemetry collection",
              "Event enrichment",
              "Noise filtering",
              "Rule scoring",
              "ML risk aggregation",
              "AI intent analysis",
              "Deception strategy",
              "Decoy deployment",
              "Interception response",
            ]}
          />
        </Panel>
        <Panel title="Repository Footprint" eyebrow="Project">
          <TopLevelChart snapshot={snapshot} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Watch Surface" eyebrow="Monitoring">
          <ListRows items={snapshot?.config.watchPaths ?? []} empty="No watch paths configured" />
        </Panel>
        <Panel title="Current Decoy Surface" eyebrow="Registry">
          <DecoySummary decoys={snapshot?.decoys ?? []} />
        </Panel>
      </section>
    </div>
  );
}

function LiveOps({
  backendState,
  backendError,
  backendBusy,
  backendAction,
  lastBackendSync,
  interceptPath,
  setInterceptPath,
  runCycle,
  refreshBackend,
  runPathInterception,
  snapshot,
}) {
  const state = backendState;
  const decoyFallback = snapshot?.decoys?.[0]?.path ?? "";
  const telemetryData = Object.entries(state?.telemetry?.counts ?? {}).map(([name, value]) => ({ name, value }));
  const detections = state?.detections ?? [];
  const recentEvents = state?.telemetry?.recent_events ?? [];

  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={CircleDot} label="Backend" value={state ? "connected" : "offline"} />
        <Metric icon={Gauge} label="Risk score" value={formatRisk(state?.status?.risk_score)} />
        <Metric icon={AlertTriangle} label="Incidents" value={state?.status?.active_incidents ?? 0} />
        <Metric icon={Radar} label="Events" value={state?.status?.events_processed ?? 0} />
      </section>

      <section className="split-grid">
        <Panel title="Manual Runtime Controls" eyebrow="Connected backend">
          <div className="control-stack">
            <div className={`connection-panel ${state ? "online" : "offline"}`}>
              <strong>{state ? "Python API connected" : "Python API not connected"}</strong>
              <span>
                {state
                  ? "State refreshes automatically. Backend cycles still run only when you click Run one cycle."
                  : backendError ?? "Start dashboard_server.py manually when you want live backend data."}
              </span>
              {lastBackendSync && <span>Last API sync: {lastBackendSync}</span>}
              {backendAction === "cycle" && <span>Cycle is running. This project can take 1-3 minutes while collectors and ML models finish.</span>}
            </div>
            <div className="button-row">
              <button className="command-button" type="button" onClick={refreshBackend} disabled={backendBusy}>
                {backendAction === "sync" ? "Refreshing" : "Refresh state"}
              </button>
              <button className="command-button primary" type="button" onClick={runCycle} disabled={backendBusy}>
                {backendAction === "cycle" ? "Running cycle" : "Run one cycle"}
              </button>
            </div>
            <div className="intercept-row">
              <input
                value={interceptPath}
                onChange={(event) => setInterceptPath(event.target.value)}
                placeholder={decoyFallback || "Enter decoy path to intercept"}
              />
              <button className="command-button" type="button" onClick={runPathInterception} disabled={backendBusy}>
                {backendAction === "intercept" ? "Intercepting" : "Intercept"}
              </button>
            </div>
          </div>
        </Panel>
        <Panel title="Runtime Snapshot" eyebrow="State">
          <KeyValue label="Pipeline initialized" value={state?.runtime?.pipeline_initialized ?? false} />
          <KeyValue label="Cycle count" value={state?.runtime?.cycle_count ?? 0} />
          <KeyValue label="Last cycle" value={state?.runtime?.last_cycle_at ?? "none"} />
          <KeyValue label="Cycle latency" value={`${state?.runtime?.last_cycle_duration_ms ?? 0}ms`} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Telemetry Mix" eyebrow="Collectors">
          {telemetryData.length ? (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={telemetryData}>
                  <CartesianGrid stroke="rgba(127, 139, 153, 0.18)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: "currentColor", fontSize: 11 }} />
                  <YAxis tick={{ fill: "currentColor", fontSize: 11 }} />
                  <Tooltip cursor={{ fill: "rgba(64, 201, 190, 0.08)" }} />
                  <Bar dataKey="value" fill="#2bb8a8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No cycle telemetry yet" detail="Click Run one cycle after starting dashboard_server.py." />
          )}
        </Panel>
        <Panel title="AI And Deception Output" eyebrow="Analysis">
          <KeyValue label="Intent" value={state?.analysis?.intent ?? "not generated"} />
          <KeyValue label="Attack stage" value={state?.analysis?.attack_stage ?? "not generated"} />
          <KeyValue label="Confidence" value={state?.analysis?.confidence ?? "not generated"} />
          <KeyValue label="Decoys deployed" value={state?.deployment?.decoys?.length ?? snapshot?.decoys?.length ?? 0} />
          <KeyValue label="Rules armed" value={state?.deployment?.rules?.length ?? 0} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Recent Events" eyebrow="Evidence">
          <EventList events={recentEvents} />
        </Panel>
        <Panel title="Accepted Detections" eyebrow="Detection">
          <DetectionList detections={detections} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Interception Result" eyebrow="Response">
          {state?.interception ? (
            <div className="result-box">
              <strong>{state.interception.path}</strong>
              <pre>{String(state.interception.result ?? "")}</pre>
            </div>
          ) : (
            <EmptyState title="No interception executed" detail="Run an interception against a registered decoy path." />
          )}
        </Panel>
        <Panel title="Backend Errors" eyebrow="Diagnostics">
          <ListRows items={state?.errors ?? (backendError ? [backendError] : [])} empty="No backend errors reported" />
        </Panel>
      </section>
    </div>
  );
}

function WorkflowView({ snapshot }) {
  const graph = useMemo(() => buildWorkflowGraph(snapshot), [snapshot]);
  return (
    <div className="view-stack">
      <section className="flow-canvas">
        <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView nodesDraggable={false} proOptions={{ hideAttribution: true }}>
          <Background gap={20} color="rgba(139, 151, 166, 0.22)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </section>
      <section className="three-grid">
        <Panel title="Conditional Gates" eyebrow="Routing">
          <ListRows items={snapshot?.workflow.conditionals ?? []} empty="No conditional routes found" />
        </Panel>
        <Panel title="State Contract" eyebrow="SecuritySystemState">
          <ListRows
            items={[
              "raw_events",
              "enriched_events",
              "detections",
              "alert_records",
              "risk_score",
              "analysis",
              "strategy",
              "deployment",
              "interception_result",
            ]}
            empty="No state keys found"
          />
        </Panel>
        <Panel title="Runtime Boundary" eyebrow="Process">
          <KeyValue label="Entry" value={snapshot?.runtime.entrypoint ?? "main.py"} />
          <KeyValue label="Mode" value={snapshot?.runtime.mode ?? "console"} />
          <KeyValue label="Auto start" value={snapshot?.runtime.startsBackendAutomatically ? "enabled" : "disabled"} />
        </Panel>
      </section>
    </div>
  );
}

function DeceptionView({ snapshot }) {
  const decoys = snapshot?.decoys ?? [];
  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={Target} label="Registered decoys" value={decoys.length} />
        <Metric icon={FileWarning} label="High sensitivity" value={decoys.filter((decoy) => decoy.sensitivity === "high").length} />
        <Metric icon={Sparkles} label="High realism" value={decoys.filter((decoy) => decoy.realism_level === "high").length} />
        <Metric icon={Zap} label="Supported types" value={new Set(decoys.map((decoy) => decoy.file_type)).size} />
      </section>

      <section className="data-table">
        <div className="table-header decoy-columns">
          <span>Virtual path</span>
          <span>Type</span>
          <span>Content</span>
          <span>Sensitivity</span>
          <span>Real path</span>
        </div>
        {decoys.length ? (
          decoys.map((decoy) => (
            <div className="table-row decoy-columns" key={decoy.path}>
              <strong>{decoy.path}</strong>
              <span>{decoy.file_type ?? "unknown"}</span>
              <span>{decoy.content_type ?? "generic"}</span>
              <Badge tone={decoy.sensitivity === "high" ? "danger" : "neutral"}>{decoy.sensitivity ?? "medium"}</Badge>
              <span className="mono">{decoy.real_os_path ?? "not mapped"}</span>
            </div>
          ))
        ) : (
          <EmptyState title="No decoys registered" detail="registry.json is empty in this snapshot." />
        )}
      </section>
    </div>
  );
}

function ModelsView({ snapshot }) {
  const models = snapshot?.models ?? [];
  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={Brain} label="Model artifacts" value={models.length} />
        <Metric icon={ShieldCheck} label="Present" value={models.filter((model) => model.exists).length} />
        <Metric icon={AlertTriangle} label="Missing" value={models.filter((model) => !model.exists).length} />
        <Metric icon={Activity} label="Poll interval" value={`${snapshot?.config.pollInterval ?? "?"}s`} />
      </section>
      <section className="split-grid">
        <Panel title="Artifact Health" eyebrow="ML">
          <div className="row-list">
            {models.map((model) => (
              <div className="model-row" key={model.path}>
                <div>
                  <strong>{model.path.split("/").pop()}</strong>
                  <span>{model.path}</span>
                </div>
                <Badge tone={model.exists ? "good" : "danger"}>{model.exists ? "present" : "missing"}</Badge>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Configuration" eyebrow="Runtime">
          <KeyValue label="Version" value={snapshot?.config.version ?? "unknown"} />
          <KeyValue label="Environment" value={snapshot?.config.environment ?? "unknown"} />
          <KeyValue label="Model config" value={snapshot?.config.modelConfig ? "available" : "missing"} />
          <KeyValue label="Threshold config" value={snapshot?.config.thresholds ? "available" : "missing"} />
        </Panel>
      </section>
    </div>
  );
}

function CodeIntel({ snapshot, modules }) {
  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={Database} label="Repo files" value={snapshot?.counts.files ?? 0} />
        <Metric icon={Code2} label="Key modules" value={modules.length} />
        <Metric icon={TerminalSquare} label="Tests" value={snapshot?.tests.reduce((sum, test) => sum + test.tests.length, 0) ?? 0} />
        <Metric icon={HardDrive} label="Top folders" value={snapshot?.topLevel.length ?? 0} />
      </section>
      <section className="module-grid">
        {modules.map((module) => (
          <article className="module-card" key={module.path}>
            <div className="module-topline">
              <Badge tone={module.exists ? "good" : "danger"}>{module.exists ? "present" : "missing"}</Badge>
              <span>{module.lines ?? 0} lines</span>
            </div>
            <h3>{module.path}</h3>
            <p>{module.classes?.length ? `Classes: ${module.classes.join(", ")}` : "No classes detected"}</p>
            <p>{module.functions?.length ? `Functions: ${module.functions.slice(0, 6).join(", ")}` : "No top-level functions detected"}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function RisksView({ snapshot }) {
  const risks = snapshot?.risks ?? [];
  return (
    <div className="view-stack">
      <section className="metrics-grid">
        <Metric icon={AlertTriangle} label="Findings" value={risks.length} />
        <Metric icon={FileWarning} label="High" value={risks.filter((risk) => risk.severity === "high").length} />
        <Metric icon={Network} label="Integration" value={risks.filter((risk) => risk.area.includes("frontend")).length} />
        <Metric icon={ShieldCheck} label="Tests" value={snapshot?.tests.length ?? 0} />
      </section>
      <section className="risk-list">
        {risks.length ? risks.map((risk) => <RiskCard risk={risk} key={`${risk.area}-${risk.title}`} />) : <EmptyState title="No snapshot findings" detail="The scanner did not detect configured risk rules." />}
      </section>
    </div>
  );
}

function Panel({ title, eyebrow, children }) {
  return (
    <section className="panel">
      <div className="eyebrow">{eyebrow}</div>
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="metric">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Badge({ tone, children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function StepList({ steps }) {
  return (
    <div className="step-list">
      {steps.map((step, index) => (
        <div className="step" key={step}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <strong>{step}</strong>
          {index < steps.length - 1 && <ChevronRight size={15} />}
        </div>
      ))}
    </div>
  );
}

function TopLevelChart({ snapshot }) {
  const data = (snapshot?.topLevel ?? []).slice(0, 8);
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(127, 139, 153, 0.18)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "currentColor", fontSize: 11 }} />
          <YAxis tick={{ fill: "currentColor", fontSize: 11 }} />
          <Tooltip cursor={{ fill: "rgba(64, 201, 190, 0.08)" }} />
          <Bar dataKey="files" fill="#2bb8a8" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DecoySummary({ decoys }) {
  const data = [
    { name: "High", value: decoys.filter((decoy) => decoy.sensitivity === "high").length },
    { name: "Medium", value: decoys.filter((decoy) => decoy.sensitivity !== "high").length },
  ];
  return (
    <div className="donut-row">
      <ResponsiveContainer width={150} height={150}>
        <PieChart>
          <Pie data={data} dataKey="value" innerRadius={46} outerRadius={68} paddingAngle={4}>
            <Cell fill="#e05b55" />
            <Cell fill="#2bb8a8" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="row-list">
        {data.map((item) => (
          <KeyValue key={item.name} label={item.name} value={item.value} />
        ))}
      </div>
    </div>
  );
}

function ListRows({ items, empty }) {
  if (!items.length) return <EmptyState title={empty} detail="" />;
  return (
    <div className="row-list">
      {items.map((item) => (
        <div className="simple-row" key={item}>
          <span className="mono">{item}</span>
        </div>
      ))}
    </div>
  );
}

function EventList({ events }) {
  if (!events.length) return <EmptyState title="No events in latest state" detail="Run a manual backend cycle to collect telemetry." />;
  return (
    <div className="row-list">
      {events.slice(0, 10).map((event, index) => (
        <div className="event-row" key={`${event.type}-${event.timestamp}-${index}`}>
          <div>
            <strong>{event.file_path || event.process_name || event.remote_ip || event.type}</strong>
            <span>{event.cmdline || event.action || event.status || "collector event"}</span>
          </div>
          <Badge tone="neutral">{event.type}</Badge>
        </div>
      ))}
    </div>
  );
}

function DetectionList({ detections }) {
  if (!detections.length) return <EmptyState title="No accepted detections yet" detail="The latest backend state has not produced suspicious detections." />;
  return (
    <div className="row-list">
      {detections.slice(0, 10).map((detection, index) => (
        <div className="event-row" key={`${detection.event?.type}-${index}`}>
          <div>
            <strong>{detection.event?.file_path || detection.event?.process_name || detection.event?.remote_ip || detection.event?.type}</strong>
            <span>{[...(detection.reasons ?? []), ...(detection.rare_patterns ?? [])].join(", ") || "No reason emitted"}</span>
          </div>
          <Badge tone={detection.severity === "alert" ? "danger" : "neutral"}>{detection.severity}</Badge>
        </div>
      ))}
    </div>
  );
}

function KeyValue({ label, value }) {
  return (
    <div className="key-value">
      <span>{label}</span>
      <strong>{String(value)}</strong>
    </div>
  );
}

function RiskCard({ risk }) {
  return (
    <article className="risk-card">
      <div>
        <Badge tone={risk.severity === "high" ? "danger" : "neutral"}>{risk.severity}</Badge>
        <span className="risk-area">{risk.area}</span>
      </div>
      <h3>{risk.title}</h3>
      <p>{risk.evidence}</p>
    </article>
  );
}

function EmptyState({ title, detail }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail && <span>{detail}</span>}
    </div>
  );
}

function buildWorkflowGraph(snapshot) {
  const nodes = (snapshot?.workflow.nodes.length ? snapshot.workflow.nodes : Object.keys(workflowLabels)).map((node, index) => ({
    id: node,
    position: { x: (index % 5) * 220, y: Math.floor(index / 5) * 150 },
    data: { label: workflowLabels[node] ?? node },
    className: "flow-node",
  }));
  const edges = nodes.slice(0, -1).map((node, index) => ({
    id: `${node.id}-${nodes[index + 1].id}`,
    source: node.id,
    target: nodes[index + 1].id,
    animated: index >= 5,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));
  return { nodes, edges };
}

function derivePosture(snapshot, backendState) {
  if (backendState) {
    const level = backendState.status?.threat_level ?? "quiet";
    if (level === "critical" || level === "high") {
      return {
        label: `${level} threat`,
        tone: "danger",
        summary: "The React console is connected to the manual Python API and the latest backend state contains active risk.",
      };
    }
    return {
      label: "Backend connected",
      tone: "good",
      summary: "Manual backend API is available. The frontend will run cycles only when you click a command.",
    };
  }
  if (!snapshot) {
    return {
      label: "Loading snapshot",
      tone: "neutral",
      summary: "Reading repository intelligence from the generated frontend snapshot.",
    };
  }
  if (snapshot.risks.some((risk) => risk.severity === "high")) {
    return {
      label: "High attention",
      tone: "danger",
      summary: "The deception workflow is present, with high-impact runtime risks visible in the current tree.",
    };
  }
  return {
    label: "Snapshot ready",
    tone: "good",
    summary: "Frontend is reading repository state only; no backend process is started by this console.",
  };
}

function formatRisk(value) {
  if (value === undefined || value === null) return "0.00";
  return Number(value).toFixed(2);
}

export default App;
