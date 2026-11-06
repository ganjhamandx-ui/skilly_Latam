$ErrorActionPreference = 'Stop'
$raiz = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$carpeta = Join-Path $raiz ('.skilly_backups\sonar_export_test_' + [guid]::NewGuid().ToString('N'))
$scriptCopia = Join-Path $carpeta 'tools\quality\sonar_local.ps1'
New-Item -ItemType Directory -Path (Split-Path $scriptCopia) | Out-Null
New-Item -ItemType Directory -Path (Join-Path $carpeta '.scannerwork') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $carpeta 'resultados_simulados') | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'sonar_local.ps1') -Destination $scriptCopia
'sonar.projectKey=Skilly' | Set-Content -LiteralPath (Join-Path $carpeta 'sonar-project.properties') -Encoding UTF8
@{run_dir=(Join-Path $carpeta 'resultados_simulados')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $carpeta '.skilly-active-context.tmp') -Encoding UTF8
"projectKey=Skilly`nceTaskId=tarea-simulada" | Set-Content -LiteralPath (Join-Path $carpeta '.scannerwork\report-task.txt') -Encoding UTF8
$tokenPrevio = [Environment]::GetEnvironmentVariable('SONAR_TOKEN','Process')
$tokenSintetico = [guid]::NewGuid().ToString('N')
$global:SkillySonarExportMockToken = $tokenSintetico
$global:SkillySonarExportMockCalls = @()
$global:SkillySonarExportMockMode = 'SUCCESS'
$global:SkillySonarExportMockChecks = @()

function Comprobar([string]$Nombre, [bool]$Correcto) {
    $global:SkillySonarExportMockChecks += [pscustomobject]@{name=$Nombre;passed=$Correcto}
    if (-not $Correcto) { throw "Fallo de prueba: $Nombre" }
}

# Todas las respuestas son fixtures sinteticas: ninguna llamada llega a red.
function Get-MockSonarResponse($Uri) {
    $global:SkillySonarExportMockCalls += $Uri
    if ($Uri -notlike 'http://127.0.0.1:9000/*') { throw 'Origen inesperado' }
    switch -Wildcard ($Uri) {
        '*/api/system/status' { return @{status='UP'} }
        '*/api/authentication/validate' { return @{valid=$true} }
        '*/api/components/show?*' { return @{component=@{key='Skilly';name='Nombre visible simulado';qualifier='TRK'}} }
        '*/api/ce/task?*' {
            return @{task=@{status=$global:SkillySonarExportMockMode;analysisId='analisis-simulado';componentKey='Skilly';warningCount=1;warnings=@("Aviso sintetico token=$global:SkillySonarExportMockToken");scannerContext="sonar.sources=backend,frontend`nsonar.projectKey=Skilly`nsonar.login=$global:SkillySonarExportMockToken"}}
        }
        '*/api/qualitygates/project_status?analysisId=analisis-simulado' { return @{projectStatus=@{status='ERROR';conditions=@(@{metricKey='new_coverage';status='ERROR';actualValue='0';errorThreshold='80'})}} }
        '*/api/new_code_periods/show?*' { return @{projectKey='Skilly';type='PREVIOUS_VERSION';inherited=$true} }
        '*/api/project_analyses/search?*' { return @{analyses=@(@{key='analisis-simulado';date='2026-01-01T00:00:00+0000';revision='revision-simulada';projectVersion='1.0'})} }
        '*/api/measures/component[?]*' { return @{component=@{measures=@(@{metric='coverage';value='0'})}} }
        '*/api/issues/search?*' {
            $esNuevo = $Uri.Contains('inNewCodePeriod=true')
            $total = if ($esNuevo) { 425 } else { 623 }
            $inicio = if ($Uri.Contains('&p=2')) { 500 } else { 0 }
            $fin = [Math]::Min($inicio + 500, $total)
            $items = @()
            for ($numero=$inicio; $numero -lt $fin; $numero++) {
                $items += @{key="incidencia-$numero";rule='css:S4666';component='Skilly:frontend/src/prueba.css';line=($numero+1);severity='MAJOR';type='CODE_SMELL';status='OPEN'}
            }
            return @{total=$total;issues=$items}
        }
        '*/api/measures/component_tree?*' { return @{paging=@{total=1};components=@(@{key='Skilly:backend/prueba.py';path='backend/prueba.py';language='py';qualifier='FIL';measures=@(@{metric='lines_to_cover';value='10'})})} }
        default { throw 'Endpoint simulado desconocido' }
    }
}

function Invoke-RestMethod($Uri, $Headers, $TimeoutSec, $MaximumRedirection) {
    Get-MockSonarResponse $Uri | ConvertTo-Json -Depth 12 | ConvertFrom-Json
}

try {
    [Environment]::SetEnvironmentVariable('SONAR_TOKEN',$tokenSintetico,'Process')
    & $scriptCopia -SoloResultados | Out-Null
    $puntero = Get-Content -LiteralPath (Join-Path $carpeta '.skilly-sonar-result.tmp') -Raw -Encoding UTF8 | ConvertFrom-Json
    $texto = Get-Content -LiteralPath (Join-Path $puntero.directory 'resultado.json') -Raw -Encoding UTF8
    $reporte = $texto | ConvertFrom-Json
    Comprobar 'pagination_all_623' ($reporte.issues.Count -eq 623 -and $reporte.issue_export_complete)
    Comprobar 'new_code_425_separate' ($reporte.new_issues.Count -eq 425 -and $reporte.new_issues_export_complete)
    Comprobar 'gate_bound_to_analysis' ($global:SkillySonarExportMockCalls -contains 'http://127.0.0.1:9000/api/qualitygates/project_status?analysisId=analisis-simulado')
    Comprobar 'display_name_from_api' ($reporte.identity.key -ceq 'Skilly' -and $reporte.identity.name -ceq 'Nombre visible simulado')
    Comprobar 'private_fields_not_exported' (-not $texto.Contains($tokenSintetico) -and -not $texto.Contains('sonar.login'))
    Comprobar 'scope_exported' ($reporte.scanner_scope.'sonar.sources' -ceq 'backend,frontend')
    Comprobar 'groups_complete' ($reporte.by_rule[0].Count -eq 623 -and $reporte.by_file[0].Count -eq 623)
    Comprobar 'no_false_scanner_rerun' (-not $reporte.scanner_rerun -and $reporte.compute_completed)
    Comprobar 'environment_restored' ([Environment]::GetEnvironmentVariable('SONAR_TOKEN','Process') -ceq $tokenSintetico)
    $global:SkillySonarExportMockMode = 'FAILED'
    & $scriptCopia -SoloResultados | Out-Null
    $puntero = Get-Content -LiteralPath (Join-Path $carpeta '.skilly-sonar-result.tmp') -Raw -Encoding UTF8 | ConvertFrom-Json
    $fallido = Get-Content -LiteralPath (Join-Path $puntero.directory 'resultado.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Comprobar 'failed_task_not_approved' (-not $fallido.scanner_completed -and -not $fallido.compute_completed -and $null -eq $fallido.quality_gate)
    'sonar.projectKey=OtraClaveSimulada' | Set-Content -LiteralPath (Join-Path $carpeta 'sonar-project.properties') -Encoding UTF8
    $antes = $global:SkillySonarExportMockCalls.Count
    $bloqueado = $false
    try { & $scriptCopia -SoloResultados | Out-Null } catch { $bloqueado = $true }
    Comprobar 'key_mismatch_blocks_before_network' ($bloqueado -and $global:SkillySonarExportMockCalls.Count -eq $antes)
    [pscustomobject]@{passed=$true;mocked_api=$true;real_sonar_analysis=$false;checks=$global:SkillySonarExportMockChecks} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $carpeta 'resultado_test.json') -Encoding UTF8
    Write-Output "SONAR_EXPORT_MOCK_CHECKS $($global:SkillySonarExportMockChecks.Count)"
    Write-Output "TEST_EVIDENCE $carpeta"
} finally {
    [Environment]::SetEnvironmentVariable('SONAR_TOKEN',$tokenPrevio,'Process')
}
