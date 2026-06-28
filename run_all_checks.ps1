$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment Python not found at $python"
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$cacheDir = Join-Path $repoRoot "cache"
$demoRoot = Join-Path $repoRoot "demo_shared"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
New-Item -ItemType Directory -Force -Path $demoRoot | Out-Null

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Details
    )

    $results.Add([pscustomobject]@{
        Check = $Name
        Passed = $Passed
        Details = $Details
    }) | Out-Null
}

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Body
    )

    Write-Host ""
    Write-Host "=== $Name ==="

    try {
        $details = & $Body
        Add-Result -Name $Name -Passed $true -Details ([string]$details)
        Write-Host "[PASS] $Name"
        if ($details) {
            Write-Host $details
        }
    }
    catch {
        $msg = $_.Exception.Message
        Add-Result -Name $Name -Passed $false -Details $msg
        Write-Host "[FAIL] $Name"
        Write-Host $msg
    }
}

function Run-PythonCommand {
    param(
        [string[]]$Arguments,
        [int]$TimeoutSeconds = 180
    )

    $outFile = Join-Path $cacheDir ("check_" + [guid]::NewGuid().ToString() + ".out")
    $errFile = Join-Path $cacheDir ("check_" + [guid]::NewGuid().ToString() + ".err")
    $proc = $null

    try {
        $proc = Start-Process -FilePath $python `
            -ArgumentList $Arguments `
            -WorkingDirectory $repoRoot `
            -PassThru `
            -RedirectStandardOutput $outFile `
            -RedirectStandardError $errFile

        if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
            try { $proc.Kill() } catch {}
            throw "Timed out after $TimeoutSeconds seconds: python $($Arguments -join ' ')"
        }

        $stdout = if (Test-Path $outFile) { Get-Content $outFile -Raw } else { "" }
        $stderr = if (Test-Path $errFile) { Get-Content $errFile -Raw } else { "" }

        return [pscustomobject]@{
            ExitCode = [int]$proc.ExitCode
            StdOut = $stdout
            StdErr = $stderr
        }
    }
    finally {
        Remove-Item $outFile -ErrorAction SilentlyContinue
        Remove-Item $errFile -ErrorAction SilentlyContinue
    }
}

function Run-PythonCode {
    param(
        [string]$Code,
        [int]$TimeoutSeconds = 180
    )

    $tempScript = Join-Path $cacheDir ("inline_" + [guid]::NewGuid().ToString() + ".py")
    try {
        $bootstrap = @"
import os
import sys
os.chdir(r'$repoRoot')
sys.path.insert(0, r'$repoRoot')

"@
        Set-Content -Path $tempScript -Value ($bootstrap + $Code) -Encoding UTF8
        return Run-PythonCommand -Arguments @("""$tempScript""") -TimeoutSeconds $TimeoutSeconds
    }
    finally {
        Remove-Item $tempScript -ErrorAction SilentlyContinue
    }
}

function Assert-ExitZero {
    param(
        $RunResult,
        [string]$Context
    )

    if (($null -eq $RunResult.ExitCode) -or ($RunResult.ExitCode -ne 0)) {
        $msg = "$Context failed with exit code $($RunResult.ExitCode)."
        if ($RunResult.StdErr) {
            $msg += "`nSTDERR:`n$($RunResult.StdErr.Trim())"
        }
        if ($RunResult.StdOut) {
            $msg += "`nSTDOUT:`n$($RunResult.StdOut.Trim())"
        }
        throw $msg
    }
}

Invoke-Check "Environment Prerequisites" {
    $envFile = Join-Path $repoRoot ".env"
    if (-not (Test-Path $envFile)) {
        throw ".env file is missing."
    }

    $envRaw = Get-Content $envFile -Raw
    if ($envRaw -notmatch "(?m)^\s*OPENAI_API_KEY\s*=\s*\S+") {
        throw "OPENAI_API_KEY is missing from .env."
    }

    $requiredModels = @(
        "ml\ml_models\file_model\file_hybrid_final.pkl",
        "ml\ml_models\process_model\process_hybrid_final.pkl",
        "ml\ml_models\network_model\network_hybrid_model.pkl"
    )

    $missing = @()
    foreach ($model in $requiredModels) {
        $full = Join-Path $repoRoot $model
        if (-not (Test-Path $full)) {
            $missing += $model
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing model artifacts: $($missing -join ', ')"
    }

    return "OPENAI_API_KEY present and all required model artifacts exist."
}

Invoke-Check "LLM Config" {
    $llmClientPath = Join-Path $repoRoot "utils\llm_client.py"
    $llmClient = Get-Content $llmClientPath -Raw

    if ($llmClient -notmatch 'ANALYSIS_MODEL\s*=\s*"gpt-4o-mini"') {
        throw "ANALYSIS_MODEL is not set to gpt-4o-mini."
    }
    if ($llmClient -notmatch 'GENERATION_MODEL\s*=\s*"gpt-4o-mini"') {
        throw "GENERATION_MODEL is not set to gpt-4o-mini."
    }
    if ($llmClient -match 'from groq import Groq') {
        throw "Groq import still present in utils\\llm_client.py."
    }

    return "Shared LLM client is configured for OpenAI gpt-4o-mini."
}

Invoke-Check "Pytest Strategy" {
    $run = Run-PythonCommand -Arguments @("-m", "pytest", "tests\test_strategy.py", "-q") -TimeoutSeconds 120
    Assert-ExitZero -RunResult $run -Context "Strategy tests"
    if ($run.StdOut -notmatch "passed") {
        throw "Strategy tests did not report passing output.`n$($run.StdOut)"
    }
    return $run.StdOut.Trim()
}

Invoke-Check "Pytest Deployment" {
    $run = Run-PythonCommand -Arguments @("-m", "pytest", "tests\test_deployment_agent.py", "-q") -TimeoutSeconds 120
    Assert-ExitZero -RunResult $run -Context "Deployment tests"
    if ($run.StdOut -notmatch "passed") {
        throw "Deployment tests did not report passing output.`n$($run.StdOut)"
    }
    return $run.StdOut.Trim()
}

Invoke-Check "Pipeline Demo" {
    $run = Run-PythonCommand -Arguments @("tests\test_pipeline.py") -TimeoutSeconds 180
    Assert-ExitZero -RunResult $run -Context "Pipeline demo"
    if ($run.StdOut -notmatch "DECISION: fake") {
        throw "Pipeline demo did not hit fake interception.`n$($run.StdOut)"
    }
    if ($run.StdOut -notmatch "GENERATED FILES") {
        throw "Pipeline demo did not print generated file summary.`n$($run.StdOut)"
    }
    return "Fake interception and generation confirmed."
}

Invoke-Check "Attacker Simulation" {
    $run = Run-PythonCommand -Arguments @("tests\test_pipeline_attacker.py") -TimeoutSeconds 180
    Assert-ExitZero -RunResult $run -Context "Attacker simulation"
    if ($run.StdOut -notmatch "SOURCE: DECOY / GENERATED") {
        throw "Attacker simulation did not return generated decoy content.`n$($run.StdOut)"
    }
    return "Decoy interception confirmed for attacker simulation."
}

Invoke-Check "Watcher Demo" {
    $stdoutPath = Join-Path $cacheDir "run_event_pipeline.out"
    $stderrPath = Join-Path $cacheDir "run_event_pipeline.err"
    Remove-Item $stdoutPath -ErrorAction SilentlyContinue
    Remove-Item $stderrPath -ErrorAction SilentlyContinue

    $proc = Start-Process -FilePath $python `
        -ArgumentList @("-u", "tests\run_event_pipeline.py") `
        -WorkingDirectory $repoRoot `
        -PassThru `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    try {
        Start-Sleep -Seconds 3
        New-Item -ItemType Directory -Force -Path (Join-Path $demoRoot "logs") | Out-Null
        Set-Content -Path (Join-Path $demoRoot "logs\sec_audit.log") -Value "trigger"
        Start-Sleep -Seconds 5
    }
    finally {
        if (-not $proc.HasExited) {
            try { Stop-Process -Id $proc.Id -Force } catch {}
        }
    }

    $stdout = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw } else { "" }
    $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw } else { "" }

    if ([string]::IsNullOrWhiteSpace([string]$stderr) -eq $false) {
        throw "Watcher demo emitted stderr.`n$stderr"
    }
    if ($stdout -notmatch "EVENT DETECTED:") {
        throw "Watcher demo did not detect file events.`n$stdout"
    }
    if ($stdout -notmatch "DECISION: fake") {
        throw "Watcher demo did not trigger fake interception.`n$stdout"
    }
    return "Watcher detected events and returned fake content."
}

Invoke-Check "LangGraph Full Cycle" {
    $code = @"
from langgraph_pipeline import LangGraphSecurityPipeline
pipeline = LangGraphSecurityPipeline()
ev1 = {'type':'process_sample','timestamp':0,'data':{'pid':1111,'process_name':'powershell.exe','parent_process':'winword.exe','cmdline':'powershell.exe -enc aaa','cpu_percent':91,'memory_mb':650}}
ev2 = {'type':'process_sample','timestamp':0,'data':{'pid':2222,'process_name':'powershell.exe','parent_process':'winword.exe','cmdline':'powershell.exe -enc bbb','cpu_percent':92,'memory_mb':670}}
state = pipeline.run_monitor_cycle({'input_events':[ev1, ev2]})
print('RISK', state.get('risk_score'))
print('HAS_ANALYSIS', bool(state.get('analysis')))
print('HAS_STRATEGY', bool(state.get('strategy')))
print('DEPLOYED_FILES', len(state.get('deployment', {}).get('decoy_registry', {})))
"@
    $run = Run-PythonCode -Code $code -TimeoutSeconds 180
    Assert-ExitZero -RunResult $run -Context "LangGraph full cycle"
    if ($run.StdOut -notmatch "HAS_ANALYSIS True") {
        throw "LangGraph full cycle did not produce analysis.`n$($run.StdOut)"
    }
    if ($run.StdOut -notmatch "HAS_STRATEGY True") {
        throw "LangGraph full cycle did not produce strategy.`n$($run.StdOut)"
    }
    return "Alert, analysis, strategy, and deployment path confirmed."
}

Invoke-Check "LangGraph Interception Mode" {
    $code = @"
from langgraph_pipeline import LangGraphSecurityPipeline
pipeline = LangGraphSecurityPipeline()
state = pipeline.intercept_access({
    'request_path': '/shared/admin/backup_credentials.txt',
    'analysis': {'intent': 'data_exfiltration', 'attack_stage': 'collection', 'confidence': 0.9},
    'strategy': {'execution_plan': {'files_to_create': [
        {'absolute_path': '/shared/admin/backup_credentials.txt', 'file_type': 'txt', 'content_profile': 'credentials', 'realism': 'high', 'size_bytes_target': 800}
    ]}}
})
print('HAS_DEPLOYMENT', bool(state.get('deployment', {}).get('decoy_registry')))
print('HAS_RESULT', bool(state.get('interception_result')))
"@
    $run = Run-PythonCode -Code $code -TimeoutSeconds 180
    Assert-ExitZero -RunResult $run -Context "LangGraph interception mode"
    if ($run.StdOut -notmatch "HAS_DEPLOYMENT True") {
        throw "LangGraph interception mode did not build deployment state.`n$($run.StdOut)"
    }
    if ($run.StdOut -notmatch "HAS_RESULT True") {
        throw "LangGraph interception mode did not return interception content.`n$($run.StdOut)"
    }
    return "Strategy -> deployment -> interception path confirmed."
}

Invoke-Check "Main Startup Smoke Test" {
    $stdoutPath = Join-Path $cacheDir "main_smoke.out"
    $stderrPath = Join-Path $cacheDir "main_smoke.err"
    Remove-Item $stdoutPath -ErrorAction SilentlyContinue
    Remove-Item $stderrPath -ErrorAction SilentlyContinue

    $proc = Start-Process -FilePath $python `
        -ArgumentList @("-u", "main.py") `
        -WorkingDirectory $repoRoot `
        -PassThru `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    try {
        Start-Sleep -Seconds 6
        if ($proc.HasExited) {
            $stdout = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw } else { "" }
            $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw } else { "" }
            throw "main.py exited early.`nSTDOUT:`n$stdout`nSTDERR:`n$stderr"
        }
    }
    finally {
        if (-not $proc.HasExited) {
            try { Stop-Process -Id $proc.Id -Force } catch {}
        }
    }

    $stdout = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw } else { "" }
    $stderr = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw } else { "" }

    if ([string]::IsNullOrWhiteSpace([string]$stderr) -eq $false) {
        throw "main.py emitted stderr during startup.`n$stderr"
    }
    if ($stdout -notmatch "Agentic Security System Started") {
        throw "main.py did not print startup banner.`n$stdout"
    }
    if ($stdout -notmatch "Version:") {
        throw "main.py did not print version information.`n$stdout"
    }
    return "main.py started and stayed alive for smoke window."
}

Write-Host ""
Write-Host "=== Summary ==="

$failed = $results | Where-Object { -not $_.Passed }
foreach ($result in $results) {
    $status = if ($result.Passed) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1}" -f $status, $result.Check)
}

Write-Host ""
if ($failed.Count -gt 0) {
    Write-Host "One or more checks failed."
    exit 1
}

Write-Host "All checks passed."
exit 0
