# ─── OPENBEE — Script de lancement complet ───────────────────────────────────
# Usage : .\start.ps1
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "`n🐝 OPENBEE — Démarrage..." -ForegroundColor Yellow

# ── 1. Charger le .env ────────────────────────────────────────────────────────
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Write-Host "📄 Chargement des variables depuis .env..." -ForegroundColor Cyan
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key   = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "  ✓ $key" -ForegroundColor Green
        }
    }
} else {
    Write-Host "⚠️  Pas de fichier .env trouvé — assure-toi que les clés API sont définies." -ForegroundColor Red
}

# ── 2. Venv ───────────────────────────────────────────────────────────────────
$venvActivate = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "`n🐍 Activation du venv..." -ForegroundColor Cyan
    & $venvActivate
} else {
    Write-Host "⚠️  Venv introuvable — lance d'abord : python -m venv .venv" -ForegroundColor Red
    exit 1
}

# ── 3. Backend (Terminal séparé) ──────────────────────────────────────────────
$backendPath = "C:\Users\redab\Desktop\WorkflowApp"
Write-Host "`n🚀 Démarrage du Backend (nouveau terminal)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; Write-Host '🔌 Backend OPENBEE' -ForegroundColor Yellow; .\venv\Scripts\python openbee_backend.py"
)

# Laisser le backend démarrer
Write-Host "   ⏳ Attente 3s pour que le backend démarre..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# ── 4. Frontend Streamlit ─────────────────────────────────────────────────────
$frontendScript = Join-Path $PSScriptRoot "frontend\app_OPENBEE.py"
Write-Host "`n🎨 Démarrage du Frontend Streamlit..." -ForegroundColor Cyan
Write-Host "   → http://localhost:8501`n" -ForegroundColor Green

& (Join-Path $PSScriptRoot ".venv\Scripts\streamlit.exe") run $frontendScript
