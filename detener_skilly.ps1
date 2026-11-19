#requires -Version 5.1

<#
.SYNOPSIS
Detiene exclusivamente los procesos administrados por iniciar_skilly.ps1.

.DESCRIPTION
Valida el estado persistido, la identidad de cada PID y su comando antes de terminar
Django o Vite. No detiene procesos por nombre y nunca administra PostgreSQL.
#>

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$statePath = Join-Path $projectRoot '.skilly-runtime.tmp'
$backendPort = 57743
$frontendPort = 57744
$mutex = New-Object System.Threading.Mutex($false, 'Local\SKILLY_LATAM_57743_57744')
$mutexAcquired = $false
$failureMessage = $null

# Consulta los propietarios del puerto con un fallback compatible basado en netstat.
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

# Rechaza PID reutilizados y comandos que no correspondan al proyecto y puerto registrados.
function Get-ValidatedManagedProcess {
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
        throw "No fue posible validar la identidad del PID $($Entry.pid); no se detuvo."
    }

    if (-not $actualPath.Equals($expectedPath, [StringComparison]::OrdinalIgnoreCase) -or
        $actualStart.Ticks -ne $expectedStart.Ticks) {
        throw "El PID $($Entry.pid) fue reutilizado o cambió de identidad; no se detuvo."
    }

    $commandLine = $null
    try {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($Entry.pid)" -ErrorAction Stop
        $commandLine = [string]$processInfo.CommandLine
    } catch {
        $listeners = @(Get-PortListeners -Port ([int]$Entry.port) | Where-Object OwningProcess -eq ([int]$Entry.pid))
        if ($listeners.Count -eq 0) {
            throw "No fue posible validar el comando ni el puerto del PID $($Entry.pid); no se detuvo."
        }
    }

    if ($null -ne $commandLine) {
        if ([string]$Entry.role -in @('django', 'django_launcher')) {
            if ($commandLine -notmatch '(?i)manage\.py' -or
                $commandLine -notmatch 'runserver' -or
                $commandLine -notmatch '127\.0\.0\.2:57743' -or
                $commandLine -notmatch '(?i)--noreload') {
                throw "El comando del PID $($Entry.pid) no coincide con Django de SKILLY; no se detuvo."
            }
        } elseif ([string]$Entry.role -eq 'vite') {
            if ($commandLine -notmatch '(?i)vite\.js' -or
                $commandLine -notmatch '(?:--port\s+|--port=)57744' -or
                $commandLine -notmatch '(?i)--strictPort') {
                throw "El comando del PID $($Entry.pid) no coincide con Vite de SKILLY; no se detuvo."
            }
        } else {
            throw "El rol del PID $($Entry.pid) no está autorizado; no se detuvo."
        }
    }

    return $process
}

# Elimina solamente los logs declarados por el runtime y contenidos en la raíz de SKILLY.
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
            throw 'El estado contiene una ruta de log no autorizada; no se retiró ningún archivo.'
        }
        if (Test-Path -LiteralPath $resolved -PathType Leaf) {
            Remove-Item -LiteralPath $resolved -Force
        }
    }
}

# El mutex evita que un cierre coincida con otro inicio o cierre de los mismos procesos.
try {
    $mutexAcquired = $mutex.WaitOne([TimeSpan]::FromSeconds(15))
    if (-not $mutexAcquired) {
        throw 'Otro inicio o cierre de SKILLY sigue en curso.'
    }

    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        Write-Host 'No hay procesos de SKILLY administrados por estos scripts.'
        return
    }

    try { $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } catch {
        throw 'El estado .skilly-runtime.tmp no es JSON válido; no se detuvo ningún proceso.'
    }
    if ([int]$state.schemaVersion -ne 1 -or
        -not ([System.IO.Path]::GetFullPath([string]$state.projectRoot)).Equals(
            $projectRoot,
            [StringComparison]::OrdinalIgnoreCase
        )) {
        throw 'El estado .skilly-runtime.tmp no pertenece a esta versión o proyecto; no se detuvo ningún proceso.'
    }
    if ([int]$state.backend.port -ne $backendPort -or [int]$state.frontend.port -ne $frontendPort) {
        throw 'El estado no corresponde a los puertos definitivos; no se detuvo ningún proceso.'
    }

    $frontendProcess = Get-ValidatedManagedProcess -Entry $state.frontend
    $backendProcess = Get-ValidatedManagedProcess -Entry $state.backend
    $backendLauncherProcess = $null
    if ($state.PSObject.Properties.Name -contains 'backendLauncher') {
        $backendLauncherProcess = Get-ValidatedManagedProcess -Entry $state.backendLauncher
    }

    foreach ($process in @($frontendProcess, $backendProcess, $backendLauncherProcess)) {
        if ($null -eq $process) {
            continue
        }
        if ($null -eq (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            continue
        }
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue
        if ($null -ne (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
            throw "El PID $($process.Id) no terminó; se conservó el estado para recuperación."
        }
        Write-Host "Proceso SKILLY PID $($process.Id) detenido."
    }

    Start-Sleep -Milliseconds 500
    $remainingOwnedPorts = @()
    foreach ($port in @($backendPort, $frontendPort)) {
        $listeners = @(Get-PortListeners -Port $port)
        if ($listeners.Count -gt 0) {
            $remainingOwnedPorts += $port
            foreach ($listener in $listeners) {
                $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
                $name = if ($null -ne $process) { $process.ProcessName } else { 'desconocido' }
                Write-Host "El puerto $port sigue ocupado por PID $($listener.OwningProcess) ($name); no se intervino."
            }
        }
    }

    if ($remainingOwnedPorts.Count -gt 0) {
        throw 'Quedó un listener no administrado en un puerto definitivo; se conservó el estado para diagnóstico.'
    }

    $logs = @()
    if ($state.PSObject.Properties.Name -contains 'logFiles') {
        $logs = @($state.logFiles | ForEach-Object { [string]$_ })
    }
    Remove-SafeRuntimeLogs -Paths $logs
    Remove-Item -LiteralPath $statePath -Force
    Write-Host 'SKILLY quedó detenido. PostgreSQL y los demás programas no fueron administrados ni modificados.'
} catch {
    $failureMessage = $_.Exception.Message
} finally {
    if ($mutexAcquired) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}

if ($null -ne $failureMessage) {
    [Console]::Error.WriteLine("ERROR: $failureMessage")
    exit 1
}
