#requires -Version 5.1

<#
.SYNOPSIS
Inicia una única instancia local de Django y Vite para SKILLY LATAM.

.DESCRIPTION
Valida configuración, PostgreSQL y puertos fijos antes de iniciar procesos. Registra
PID, ejecutable y hora de inicio para que el cierre posterior solo afecte a SKILLY.
No administra PostgreSQL ni selecciona puertos alternativos.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$backendPort = 57743
$frontendPort = 57744
$backendOrigin = 'http://127.0.0.2:57743'
$frontendOrigin = 'http://127.0.0.2:57744'
$statePath = Join-Path $projectRoot '.skilly-runtime.tmp'
$statePendingPath = Join-Path $projectRoot '.skilly-runtime.pending.tmp'
$envPath = Join-Path $projectRoot '.env'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$managePath = Join-Path $projectRoot 'backend\manage.py'
$vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
$backendOutLog = Join-Path $projectRoot '.skilly-backend.out.log'
$backendErrorLog = Join-Path $projectRoot '.skilly-backend.err.log'
$frontendOutLog = Join-Path $projectRoot '.skilly-frontend.out.log'
$frontendErrorLog = Join-Path $projectRoot '.skilly-frontend.err.log'
$runtimeLogs = @($backendOutLog, $backendErrorLog, $frontendOutLog, $frontendErrorLog)
$mutex = New-Object System.Threading.Mutex($false, 'Local\SKILLY_LATAM_57743_57744')
$mutexAcquired = $false
$startedProcesses = New-Object System.Collections.Generic.List[System.Diagnostics.Process]
$backendListenerProcess = $null
$startupCompleted = $false
$failureMessage = $null

# Interpreta el archivo local sin mostrar ni registrar sus valores sensibles.
function Get-DotEnvMap {
    param([Parameter(Mandatory = $true)][string]$Path)

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line -notmatch '^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            continue
        }

        $name = $matches[1]
        $value = $matches[2].Trim()
        if ($value.Length -ge 2) {
            $first = $value.Substring(0, 1)
            $last = $value.Substring($value.Length - 1, 1)
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }
        $values[$name] = $value
    }

    return $values
}

# Obtiene propietarios de un puerto y usa netstat cuando la API de Windows no está disponible.
function Get-PortListeners {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listeners = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Sort-Object OwningProcess -Unique
    )
    if ($listeners.Count -gt 0) {
        return $listeners
    }

    $pattern = "^\s*TCP\s+(\S+):$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    $fallback = foreach ($line in (& netstat.exe -ano -p tcp)) {
        if ($line -match $pattern) {
            [pscustomobject]@{
                LocalAddress = $matches[1]
                LocalPort = $Port
                OwningProcess = [int]$matches[2]
            }
        }
    }
    return @($fallback | Sort-Object OwningProcess -Unique)
}

# Describe el proceso que impide usar un puerto fijo sin intentar terminarlo.
function Write-PortOwner {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listeners = Get-PortListeners -Port $Port
    foreach ($listener in $listeners) {
        $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        $processName = if ($null -ne $process) { $process.ProcessName } else { 'desconocido' }
        $executable = if ($null -ne $process) {
            try { $process.Path } catch { '[ruta no disponible]' }
        } else {
            '[ruta no disponible]'
        }
        $commandLine = '[línea de comandos no disponible]'
        try {
            $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction Stop
            if ($processInfo.CommandLine) {
                if ($processInfo.CommandLine -match '(?i)password|secret|token|credential|api[_-]?key') {
                    $commandLine = '[línea de comandos omitida por seguridad]'
                } else {
                    $commandLine = $processInfo.CommandLine
                }
            }
        } catch {
            # El PID, nombre y ejecutable siguen siendo suficientes para informar la colisión.
        }

        Write-Host "Puerto $Port ocupado en $($listener.LocalAddress) por PID $($listener.OwningProcess) ($processName)."
        Write-Host "  Ejecutable: $executable"
        Write-Host "  Comando: $commandLine"
    }
}

# Comprueba PID, ejecutable y hora de inicio para impedir reutilizaciones de identidad.
function Get-ManagedProcess {
    param([Parameter(Mandatory = $true)]$Entry)

    $process = Get-Process -Id ([int]$Entry.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $null
    }

    try {
        $actualPath = [System.IO.Path]::GetFullPath($process.Path)
        $expectedPath = [System.IO.Path]::GetFullPath([string]$Entry.executable)
        $actualStart = $process.StartTime.ToUniversalTime()
        $expectedStart = [DateTime]::Parse(
            [string]$Entry.startTimeUtc,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind
        ).ToUniversalTime()
    } catch {
        return $null
    }

    if (-not $actualPath.Equals($expectedPath, [StringComparison]::OrdinalIgnoreCase)) {
        return $null
    }
    if ($actualStart.Ticks -ne $expectedStart.Ticks) {
        return $null
    }

    return $process
}

# Localiza el proceso Django real aunque el ejecutable del entorno virtual actúe como lanzador.
function Get-BackendListenerProcess {
    param([Parameter(Mandatory = $true)][System.Diagnostics.Process]$Launcher)

    $listeners = @(Get-PortListeners -Port $backendPort)
    if ($listeners.Count -ne 1) {
        return $null
    }
    $candidate = Get-Process -Id ([int]$listeners[0].OwningProcess) -ErrorAction SilentlyContinue
    if ($null -eq $candidate) {
        return $null
    }
    if ($candidate.Id -eq $Launcher.Id) {
        return $candidate
    }

    try {
        $ownerInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($candidate.Id)" -ErrorAction Stop
        $ownerCommand = [string]$ownerInfo.CommandLine
        if ($ownerCommand -notmatch '(?i)manage\.py' -or
            $ownerCommand -notmatch 'runserver' -or
            $ownerCommand -notmatch '127\.0\.0\.2:57743' -or
            $ownerCommand -notmatch '(?i)--noreload') {
            return $null
        }

        $cursorProcessId = [int]$ownerInfo.ParentProcessId
        for ($level = 0; $level -lt 8 -and $cursorProcessId -gt 0; $level++) {
            if ($cursorProcessId -eq $Launcher.Id) {
                return $candidate
            }
            $parentInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$cursorProcessId" -ErrorAction Stop
            $cursorProcessId = [int]$parentInfo.ParentProcessId
        }
    } catch {
        return $null
    }

    return $null
}

# Borra únicamente logs de runtime ubicados directamente dentro de este proyecto.
function Remove-SafeRuntimeLogs {
    param([string[]]$Paths)

    $rootPrefix = $projectRoot.TrimEnd('\') + '\'
    foreach ($path in $Paths) {
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }
        $resolved = [System.IO.Path]::GetFullPath($path)
        $name = [System.IO.Path]::GetFileName($resolved)
        if (-not $resolved.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase) -or
            $name -notlike '.skilly-*.log') {
            throw "El estado contiene una ruta de log no autorizada; no se retiró ningún archivo."
        }
        if (Test-Path -LiteralPath $resolved -PathType Leaf) {
            Remove-Item -LiteralPath $resolved -Force
        }
    }
}

# Verifica disponibilidad HTTP y, cuando corresponde, el contrato JSON del endpoint CSRF.
function Test-LocalEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [switch]$RequireCsrfJson
    )

    $handler = New-Object System.Net.Http.HttpClientHandler
    $handler.UseProxy = $false
    $handler.UseCookies = $true
    $client = New-Object System.Net.Http.HttpClient($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(2)
    try {
        $response = $client.GetAsync($Uri).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            return $false
        }
        if ($RequireCsrfJson) {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            try { $data = $body | ConvertFrom-Json } catch { return $false }
            return $null -ne $data -and
                $data.PSObject.Properties.Name -contains 'csrfToken' -and
                -not [string]::IsNullOrWhiteSpace([string]$data.csrfToken)
        }
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

# Revierte solo un proceso creado durante este intento de arranque fallido.
function Stop-NewProcess {
    param([System.Diagnostics.Process]$Process)

    if ($null -eq $Process) {
        return
    }
    try {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $Process.Id -Timeout 5 -ErrorAction SilentlyContinue
        }
    } catch {
        # El cierre de recuperación no debe ocultar el error original de arranque.
    }
}

# El mutex serializa arranques concurrentes antes de consultar o reservar los puertos.
try {
    $mutexAcquired = $mutex.WaitOne([TimeSpan]::FromSeconds(15))
    if (-not $mutexAcquired) {
        throw 'Otro inicio o cierre de SKILLY sigue en curso.'
    }

    foreach ($requiredFile in @($envPath, $pythonPath, $managePath, $vitePath)) {
        if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
            throw "Falta el archivo requerido: $requiredFile"
        }
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand) {
        throw 'No se encontró node.exe en PATH.'
    }
    $nodePath = [System.IO.Path]::GetFullPath($nodeCommand.Source)

    $dotenv = Get-DotEnvMap -Path $envPath
    foreach ($secretName in @('DJANGO_SECRET_KEY', 'POSTGRES_PASSWORD')) {
        if (-not $dotenv.ContainsKey($secretName) -or [string]::IsNullOrWhiteSpace([string]$dotenv[$secretName])) {
            throw "Falta $secretName en .env. No se modificaron credenciales."
        }
    }
    $expectedPublicSettings = [ordered]@{
        DJANGO_DEBUG = 'True'
        DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,127.0.0.2'
        POSTGRES_DB = 'skilly'
        POSTGRES_USER = 'skilly_app'
        POSTGRES_HOST = '127.0.0.1'
        POSTGRES_PORT = '5432'
        POSTGRES_SCHEMA = 'skilly'
        FRONTEND_ORIGIN = $frontendOrigin
    }
    foreach ($name in $expectedPublicSettings.Keys) {
        if (-not $dotenv.ContainsKey($name) -or [string]$dotenv[$name] -ne [string]$expectedPublicSettings[$name]) {
            throw "La variable pública $name de .env no coincide con la configuración definitiva."
        }
    }

    $staleState = $null
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        try { $previousState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } catch {
            throw 'El estado .skilly-runtime.tmp no es JSON válido; no se iniciaron procesos.'
        }
        if ([int]$previousState.schemaVersion -ne 1 -or
            -not ([System.IO.Path]::GetFullPath([string]$previousState.projectRoot)).Equals(
                $projectRoot,
                [StringComparison]::OrdinalIgnoreCase
            )) {
            throw 'El estado .skilly-runtime.tmp no pertenece a esta versión o proyecto.'
        }

        $ownedBackend = Get-ManagedProcess -Entry $previousState.backend
        $ownedFrontend = Get-ManagedProcess -Entry $previousState.frontend
        $ownedBackendLauncher = $null
        if ($previousState.PSObject.Properties.Name -contains 'backendLauncher') {
            $ownedBackendLauncher = Get-ManagedProcess -Entry $previousState.backendLauncher
        }
        if ($null -ne $ownedBackend -and $null -ne $ownedFrontend) {
            $backendOwnsPort = @(Get-PortListeners -Port $backendPort | Where-Object OwningProcess -eq $ownedBackend.Id).Count -gt 0
            $frontendOwnsPort = @(Get-PortListeners -Port $frontendPort | Where-Object OwningProcess -eq $ownedFrontend.Id).Count -gt 0
            if ($backendOwnsPort -and $frontendOwnsPort) {
                Write-Host "SKILLY ya está iniciado y administrado por estos scripts."
                Write-Host "URL única: $frontendOrigin/"
                $startupCompleted = $true
                return
            }
            throw 'Existe un estado parcial administrado. Ejecuta .\detener_skilly.ps1 antes de reiniciar.'
        }
        if ($null -ne $ownedBackend -or $null -ne $ownedFrontend) {
            throw 'Existe un proceso administrado parcial. Ejecuta .\detener_skilly.ps1 antes de reiniciar.'
        }
        if ($null -ne $ownedBackendLauncher) {
            throw 'Existe un lanzador de Django administrado parcial. Ejecuta .\detener_skilly.ps1 antes de reiniciar.'
        }

        $staleState = $previousState
    }

    $busy = $false
    foreach ($port in @($backendPort, $frontendPort)) {
        if (@(Get-PortListeners -Port $port).Count -gt 0) {
            Write-PortOwner -Port $port
            $busy = $true
        }
    }
    if ($busy) {
        throw 'Los puertos definitivos están ocupados. No se seleccionó ningún puerto alternativo.'
    }

    # Retira registros antiguos solo cuando ningún servidor ocupa los puertos.
    if ($null -ne $staleState) {
        if ($staleState.PSObject.Properties.Name -contains 'logFiles') {
            Remove-SafeRuntimeLogs -Paths @($staleState.logFiles | ForEach-Object { [string]$_ })
        }
        Remove-Item -LiteralPath $statePath -Force
    }

    Remove-SafeRuntimeLogs -Paths $runtimeLogs
    if (Test-Path -LiteralPath $statePendingPath -PathType Leaf) {
        Remove-Item -LiteralPath $statePendingPath -Force
    }

    $environmentNames = @($dotenv.Keys) + @('SKILLY_API_PROXY_TARGET')
    $environmentSnapshot = @{}
    foreach ($name in $environmentNames | Sort-Object -Unique) {
        $environmentSnapshot[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }

    try {
        foreach ($name in $expectedPublicSettings.Keys) {
            [Environment]::SetEnvironmentVariable($name, [string]$expectedPublicSettings[$name], 'Process')
        }
        [Environment]::SetEnvironmentVariable('SKILLY_API_PROXY_TARGET', $backendOrigin, 'Process')

        $null = & $pythonPath -B $managePath check --verbosity 0 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw 'Django no superó manage.py check con la configuración definitiva.'
        }

        $backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @(
            '-B', $managePath, 'runserver', '127.0.0.2:57743', '--noreload'
        ) -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $backendOutLog `
            -RedirectStandardError $backendErrorLog -PassThru
        $startedProcesses.Add($backendProcess)

        $frontendProcess = Start-Process -FilePath $nodePath -ArgumentList @(
            $vitePath, '--host', '127.0.0.2', '--port', '57744', '--strictPort'
        ) -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden `
            -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrorLog -PassThru
        $startedProcesses.Add($frontendProcess)
    } finally {
        foreach ($name in $environmentSnapshot.Keys) {
            [Environment]::SetEnvironmentVariable($name, $environmentSnapshot[$name], 'Process')
        }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline) {
        $backendProcess.Refresh()
        $frontendProcess.Refresh()
        if ($backendProcess.HasExited) {
            throw 'Django terminó antes de quedar disponible en 57743.'
        }
        if ($frontendProcess.HasExited) {
            throw 'Vite terminó antes de quedar disponible en 57744.'
        }

        $candidateBackendListener = Get-BackendListenerProcess -Launcher $backendProcess
        $backendListening = $null -ne $candidateBackendListener
        $frontendListening = @(Get-PortListeners -Port $frontendPort | Where-Object OwningProcess -eq $frontendProcess.Id).Count -gt 0
        if ($backendListening -and $frontendListening -and
            (Test-LocalEndpoint -Uri "$frontendOrigin/") -and
            (Test-LocalEndpoint -Uri "$frontendOrigin/api/acceso/csrf/" -RequireCsrfJson)) {
            $backendListenerProcess = $candidateBackendListener
            if (-not @($startedProcesses | Where-Object Id -eq $backendListenerProcess.Id).Count) {
                $startedProcesses.Add($backendListenerProcess)
            }
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) {
        throw 'SKILLY no completó la verificación de disponibilidad en 45 segundos.'
    }

    $backendProcess.Refresh()
    $backendListenerProcess.Refresh()
    $frontendProcess.Refresh()
    $state = [ordered]@{
        schemaVersion = 1
        projectRoot = $projectRoot
        createdAtUtc = [DateTime]::UtcNow.ToString('o')
        frontendUrl = "$frontendOrigin/"
        backend = [ordered]@{
            role = 'django'
            pid = $backendListenerProcess.Id
            port = $backendPort
            executable = [System.IO.Path]::GetFullPath($backendListenerProcess.Path)
            startTimeUtc = $backendListenerProcess.StartTime.ToUniversalTime().ToString('o')
        }
        backendLauncher = [ordered]@{
            role = 'django_launcher'
            pid = $backendProcess.Id
            port = $backendPort
            executable = [System.IO.Path]::GetFullPath($backendProcess.Path)
            startTimeUtc = $backendProcess.StartTime.ToUniversalTime().ToString('o')
        }
        frontend = [ordered]@{
            role = 'vite'
            pid = $frontendProcess.Id
            port = $frontendPort
            executable = [System.IO.Path]::GetFullPath($frontendProcess.Path)
            startTimeUtc = $frontendProcess.StartTime.ToUniversalTime().ToString('o')
        }
        logFiles = $runtimeLogs
    }
    $json = $state | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText(
        $statePendingPath,
        $json,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Move-Item -LiteralPath $statePendingPath -Destination $statePath

    $startupCompleted = $true
    Write-Host 'SKILLY inició con la configuración definitiva.'
    Write-Host "Frontend único: $frontendOrigin/ (PID $($frontendProcess.Id))"
    Write-Host "Backend interno: $backendOrigin/ (PID $($backendListenerProcess.Id))"
    Write-Host 'PostgreSQL esperado: 127.0.0.1:5432, base skilly, esquema skilly (no administrado por este script).'
} catch {
    $failureMessage = $_.Exception.Message
} finally {
    if (-not $startupCompleted) {
        foreach ($process in @($startedProcesses) | Sort-Object Id -Descending) {
            Stop-NewProcess -Process $process
        }
        foreach ($path in @($statePendingPath)) {
            if (Test-Path -LiteralPath $path -PathType Leaf) {
                Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
            }
        }
        Remove-SafeRuntimeLogs -Paths $runtimeLogs
    }
    if ($mutexAcquired) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}

if ($null -ne $failureMessage) {
    [Console]::Error.WriteLine("ERROR: $failureMessage")
    exit 1
}
