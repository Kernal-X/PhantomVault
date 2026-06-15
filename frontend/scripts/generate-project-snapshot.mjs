import fs from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(process.cwd());
const repoRoot = path.resolve(frontendRoot, "..");
const outputDir = path.join(frontendRoot, "public");
const outputPath = path.join(outputDir, "project-snapshot.json");

const ignoredDirs = new Set([
  ".git",
  ".venv",
  "__pycache__",
  ".pytest_cache",
  "node_modules",
  "dist",
  ".vite",
  "cache",
]);

const importantPaths = [
  "main.py",
  "dashboard_server.py",
  "agents/system_agent.py",
  "langgraph_pipeline.py",
  "state_schema.py",
  "core/monitor.py",
  "collectors/process_collector.py",
  "collectors/file_collector.py",
  "collectors/network_collector.py",
  "agents/event_enrichment.py",
  "utils/filters.py",
  "detectors/scoring.py",
  "logs/logger.py",
  "ml/ml_models/aggregator_model/router.py",
  "ml/ml_models/aggregator_model/aggregator.py",
  "agents/analysis/analysis_agent.py",
  "agents/strategy/strategy_agent.py",
  "agents/deployment/deployment_agent.py",
  "agents/generation/generation_agent.py",
  "core/interception_layer.py",
  "registry.json",
  "configs/system_config.yaml",
  "configs/thresholds.yaml",
  "configs/model_config.yaml",
  "README.md",
  "system_analysis.md",
];

const modelArtifacts = [
  "ml/ml_models/file_model/file_hybrid_final.pkl",
  "ml/ml_models/process_model/process_hybrid_final.pkl",
  "ml/ml_models/network_model/network_hybrid_model.pkl",
];

function walk(dir, base = "") {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (ignoredDirs.has(entry.name)) continue;
    const abs = path.join(dir, entry.name);
    const rel = path.join(base, entry.name).replaceAll("\\", "/");
    if (entry.isDirectory()) {
      files.push(...walk(abs, rel));
    } else {
      files.push(rel);
    }
  }
  return files;
}

function readText(rel) {
  try {
    return fs.readFileSync(path.join(repoRoot, rel), "utf8");
  } catch {
    return "";
  }
}

function statProfile(rel) {
  const abs = path.join(repoRoot, rel);
  if (!fs.existsSync(abs)) {
    return { path: rel, exists: false, size: 0, modified: null, lines: 0 };
  }
  const stat = fs.statSync(abs);
  const text = stat.size < 2_000_000 ? readText(rel) : "";
  return {
    path: rel,
    exists: true,
    size: stat.size,
    modified: stat.mtime.toISOString(),
    lines: text ? text.split(/\r?\n/).length : null,
  };
}

function pythonProfile(rel) {
  const text = readText(rel);
  const lines = text.split(/\r?\n/);
  return {
    ...statProfile(rel),
    imports: [...text.matchAll(/^(?:from|import)\s+([A-Za-z0-9_./]+)/gm)].map((m) => m[1]).slice(0, 16),
    classes: [...text.matchAll(/^class\s+([A-Za-z0-9_]+)/gm)].map((m) => m[1]),
    functions: [...text.matchAll(/^def\s+([A-Za-z0-9_]+)/gm)].map((m) => m[1]),
    excerpt: lines.filter((line) => line.trim()).slice(0, 8).join("\n"),
  };
}

function parseRegistry() {
  try {
    const raw = JSON.parse(readText("registry.json") || "{}");
    return Object.entries(raw).map(([decoyPath, metadata]) => ({
      path: decoyPath,
      ...metadata,
    }));
  } catch {
    return [];
  }
}

function parseWorkflow() {
  const text = readText("langgraph_pipeline.py");
  const nodes = [...text.matchAll(/add_node\("([^"]+)"/g)].map((m) => m[1]);
  const edges = [...text.matchAll(/add_edge\(([^)]+)\)/g)].map((m) => m[1].replaceAll('"', ""));
  const conditionals = [...text.matchAll(/add_conditional_edges\(\s*"([^"]+)"/g)].map((m) => m[1]);
  return { nodes, edges, conditionals };
}

function parseConfig() {
  const systemConfig = readText("configs/system_config.yaml");
  const watchPaths = [...systemConfig.matchAll(/^\s+-\s+(.+)$/gm)].map((m) => m[1].trim());
  const version = systemConfig.match(/version:\s*([^\n]+)/)?.[1]?.trim() ?? "unknown";
  const environment = systemConfig.match(/environment:\s*([^\n]+)/)?.[1]?.trim() ?? "unknown";
  const pollInterval = systemConfig.match(/poll_interval:\s*([^\n]+)/)?.[1]?.trim() ?? "unknown";
  return {
    version,
    environment,
    pollInterval,
    watchPaths,
    raw: systemConfig,
    thresholds: readText("configs/thresholds.yaml"),
    modelConfig: readText("configs/model_config.yaml"),
  };
}

function summarizeTests(files) {
  return files
    .filter((file) => file.startsWith("tests/") && file.endsWith(".py"))
    .map((file) => {
      const text = readText(file);
      return {
        path: file,
        tests: [...text.matchAll(/def\s+(test_[A-Za-z0-9_]+)/g)].map((m) => m[1]),
        lines: text.split(/\r?\n/).length,
      };
    });
}

function buildRisks() {
  const mainText = readText("main.py");
  const deploymentText = readText("agents/deployment/deployment_agent.py");
  const apiServerExists = fs.existsSync(path.join(repoRoot, "dashboard_server.py"));
  const findings = [];
  if ((mainText.match(/if __name__ == "__main__"/g) || []).length > 1) {
    findings.push({
      severity: "high",
      area: "startup",
      title: "Duplicate main guards in main.py",
      evidence: "main.py defines two __main__ blocks and two startup paths.",
    });
  }
  if (deploymentText.includes("shutil.move(real_path, vault_path)")) {
    findings.push({
      severity: "high",
      area: "deception deployment",
      title: "Deployment can vault and replace real files",
      evidence: "DeploymentManager._materialize_file moves existing targets into .aads_vault before writing decoys.",
    });
  }
  if (!apiServerExists) {
    findings.push({
      severity: "medium",
      area: "frontend integration",
      title: "No live HTTP/WebSocket backend entrypoint in current tree",
      evidence: "The runtime is console-oriented through main.py and SystemAgent.",
    });
  }
  return findings;
}

const allFiles = walk(repoRoot).filter((file) => !file.startsWith("frontend/node_modules"));
const byTopLevel = allFiles.reduce((acc, file) => {
  const [top] = file.split("/");
  acc[top] = (acc[top] || 0) + 1;
  return acc;
}, {});

const snapshot = {
  generatedAt: new Date().toISOString(),
  repoRoot,
  counts: {
    files: allFiles.length,
    directories: Object.keys(byTopLevel).length,
    tests: allFiles.filter((file) => file.startsWith("tests/")).length,
    pythonFiles: allFiles.filter((file) => file.endsWith(".py")).length,
  },
  topLevel: Object.entries(byTopLevel)
    .map(([name, files]) => ({ name, files }))
    .sort((a, b) => b.files - a.files),
  workflow: parseWorkflow(),
  config: parseConfig(),
  modules: importantPaths.map((file) => (file.endsWith(".py") ? pythonProfile(file) : statProfile(file))),
  models: modelArtifacts.map((file) => statProfile(file)),
  decoys: parseRegistry(),
  tests: summarizeTests(allFiles),
  risks: buildRisks(),
  runtime: {
    entrypoint: "main.py",
    mode: "console",
    startsBackendAutomatically: false,
    liveApiAvailable: fs.existsSync(path.join(repoRoot, "dashboard_server.py")),
  },
};

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(snapshot, null, 2));
console.log(`Wrote ${outputPath}`);
