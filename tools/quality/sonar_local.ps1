param([switch]$SolicitarToken, [switch]$SoloResultados)
$ErrorActionPreference = 'Stop'
$servidor = 'http://127.0.0.1:9000'
$proyecto = 'Skilly'
$raiz = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$propiedades = Get-Content -LiteralPath (Join-Path $raiz 'sonar-project.properties') -Raw -Encoding UTF8
$claveConfigurada = [regex]::Match($propiedades, '(?m)^sonar\.projectKey\s*=\s*([^\r\n]+)').Groups[1].Value.Trim()
if ($claveConfigurada -cne $proyecto) { throw 'La clave del analisis no coincide con la configuracion existente. No se creara ni cambiara ningun proyecto.' }
$estado = Invoke-RestMethod -Uri "$servidor/api/system/status" -TimeoutSec 5 -MaximumRedirection 0
if ($estado.status -ne 'UP') { throw 'SonarQube local no esta disponible.' }
$tokenAnterior = [Environment]::GetEnvironmentVariable('SONAR_TOKEN','Process')
$puntero = [IntPtr]::Zero
$oculto = $null
$valoresPrivados = @()

function Proteger-Texto([string]$Texto) {
    foreach ($valor in $valoresPrivados) {
        if ($valor) { $Texto = $Texto.Replace($valor, '<redacted>') }
    }
    $Texto = $Texto -replace '(?i)(password|token|secret|authorization|api[_-]?key)\s*[=:]\s*[^\s]+', '$1=<redacted>'
    return ($Texto -replace '(?i)(https?://)[^/\s:@]+:[^/@\s]+@', '$1<redacted>@')
}

function Consultar-Api([string]$Ruta) {
    try {
        return Invoke-RestMethod -Uri ($servidor + $Ruta) -Headers $cabeceras -TimeoutSec 15 -MaximumRedirection 0
    } catch {
        $codigo = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 'unavailable' }
        throw "Consulta local no disponible (HTTP $codigo)."
    }
}

function Leer-Incidencias([string]$Filtro) {
    $lista = @()
    $total = 0
    for ($pagina = 1; $pagina -le 20; $pagina++) {
        $respuesta = Consultar-Api "/api/issues/search?componentKeys=$proyecto&resolved=false&ps=500&p=$pagina$Filtro"
        $total = [int]$respuesta.total
        $lista += @($respuesta.issues | Select-Object key,rule,component,line,severity,type,status,creationDate,updateDate)
        if ($lista.Count -ge $total) { break }
    }
    return [pscustomobject]@{total=$total;complete=($lista.Count -eq $total);issues=@($lista)}
}

try {
    if (-not $tokenAnterior) {
        if (-not $SolicitarToken) { throw 'Falta SONAR_TOKEN en este proceso. Usar -SolicitarToken en una terminal propia para entrada oculta.' }
        $oculto = Read-Host 'Token SonarQube local (entrada oculta; no pegar en el chat)' -AsSecureString
        $puntero = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($oculto)
        [Environment]::SetEnvironmentVariable('SONAR_TOKEN',[Runtime.InteropServices.Marshal]::PtrToStringBSTR($puntero),'Process')
    }
    $tokenActual = [Environment]::GetEnvironmentVariable('SONAR_TOKEN','Process')
    $valoresPrivados = @($tokenActual)
    $envRuta = Join-Path $raiz '.env'
    if (Test-Path -LiteralPath $envRuta) {
        foreach ($lineaEnv in Get-Content -LiteralPath $envRuta -Encoding UTF8) {
            if ($lineaEnv -match '^\s*[^#=]*(?i:password|passwd|secret|token|credential|api.?key)[^=]*=(.*)$') {
                $valorEnv = $Matches[1].Trim().Trim([char]34,[char]39)
                if ($valorEnv.Length -ge 4) { $valoresPrivados += $valorEnv }
            }
        }
    }
    $cabeceras = @{Authorization="Bearer $tokenActual"}
    $autenticacion = Consultar-Api '/api/authentication/validate'
    if ($autenticacion.valid -ne $true) { throw 'SonarQube local no valido el token; no se ejecutara el scanner.' }
    $identidad = Consultar-Api "/api/components/show?component=$proyecto"
    if ($identidad.component.key -cne $proyecto -or $identidad.component.qualifier -ne 'TRK') { throw 'La API no confirmo la clave del proyecto existente.' }
    $contextoRuta = Join-Path $raiz '.skilly-active-context.tmp'
    $baseResultados = if (Test-Path -LiteralPath $contextoRuta) { (Get-Content -LiteralPath $contextoRuta -Raw -Encoding UTF8 | ConvertFrom-Json).run_dir } else { $env:TEMP }
    $destino = Join-Path $baseResultados ('sonar_analisis_' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $destino -ErrorAction Stop | Out-Null
    if (-not $SoloResultados) {
        $scanner = 'C:\Users\felip\Downloads\sonar-scanner-cli-8.1\sonar-scanner-8.1.0.6389-windows-x64\bin\sonar-scanner.bat'
        $argumentosScanner = @("-Dsonar.projectBaseDir=$raiz", "-Dsonar.host.url=$servidor")
        $coberturaRuta = Join-Path $raiz '.skilly-coverage-result.tmp'
        if (Test-Path -LiteralPath $coberturaRuta) {
            $cobertura = Get-Content -LiteralPath $coberturaRuta -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($cobertura.python_xml -and (Test-Path -LiteralPath $cobertura.python_xml)) { $argumentosScanner += "-Dsonar.python.coverage.reportPaths=$($cobertura.python_xml)" }
            $rutasLcov = @()
            foreach ($rutaLcov in @($cobertura.node_lcov, $cobertura.browser_lcov)) {
                if ($rutaLcov -and (Test-Path -LiteralPath $rutaLcov)) { $rutasLcov += $rutaLcov }
            }
            if ($rutasLcov.Count) { $argumentosScanner += "-Dsonar.javascript.lcov.reportPaths=$($rutasLcov -join ',')" }
        }
        $modoAnterior = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & $scanner @argumentosScanner 2>&1 | ForEach-Object {
                $linea = Proteger-Texto "$_"
                Add-Content -LiteralPath (Join-Path $destino 'scanner.log') -Value $linea -Encoding UTF8
                Write-Output $linea
            }
        } finally { $ErrorActionPreference = $modoAnterior }
        if ($LASTEXITCODE -ne 0) { throw 'SonarScanner local no completo el analisis.' }
    }
    $resultado = [ordered]@{
        scanner_completed=$false;scanner_rerun=(-not $SoloResultados);server=$servidor;project=$proyecto
        identity=($identidad.component | Select-Object key,name,qualifier,visibility)
        compute_completed=$false;quality_gate=$null;exported_at_utc=[DateTime]::UtcNow.ToString('o')
    }
    $tareaRuta = Join-Path $raiz '.scannerwork\report-task.txt'
    if (-not (Test-Path -LiteralPath $tareaRuta)) { throw 'Falta report-task.txt: no se puede vincular la exportacion a un analisis real.' }
    $tareaTexto = Get-Content -LiteralPath $tareaRuta -Raw -Encoding UTF8
    $claveTarea = [regex]::Match($tareaTexto, '(?m)^projectKey=([^\r\n]+)').Groups[1].Value.Trim()
    $tarea = [regex]::Match($tareaTexto, '(?m)^ceTaskId=([^\r\n]+)').Groups[1].Value.Trim()
    if ($claveTarea -cne $proyecto -or $tarea -notmatch '^[A-Za-z0-9_-]+$') { throw 'El informe del scanner no corresponde a la clave verificada.' }
    $resultado.ce_task_id = $tarea
    for ($intento=0; $intento -lt 30; $intento++) {
        $estadoTarea = Consultar-Api "/api/ce/task?id=$tarea"
        if ($estadoTarea.task.status -in @('SUCCESS','FAILED','CANCELED')) { break }
        Start-Sleep -Seconds 2
    }
    $resultado.compute_status = $estadoTarea.task.status
    $resultado.compute_completed = $estadoTarea.task.status -eq 'SUCCESS'
    $resultado.scanner_completed = $resultado.compute_completed
    $resultado.analysis_id = $estadoTarea.task.analysisId
    $resultado.task_component_key = $estadoTarea.task.componentKey
    if ($resultado.task_component_key -and $resultado.task_component_key -cne $proyecto) { throw 'La tarea del servidor corresponde a otro proyecto; se detiene la exportacion.' }
    $resultado.warnings = @($estadoTarea.task.warnings | ForEach-Object { Proteger-Texto "$_" })
    $resultado.warning_count = $estadoTarea.task.warningCount
    try {
        $detalleTarea = Consultar-Api "/api/ce/task?id=$tarea&additionalFields=scannerContext"
        $permitidas = @('sonar.projectKey','sonar.projectName','sonar.projectVersion','sonar.projectBaseDir','sonar.sources','sonar.tests','sonar.exclusions','sonar.inclusions','sonar.test.inclusions','sonar.test.exclusions','sonar.coverage.exclusions','sonar.python.version','sonar.python.coverage.reportPaths','sonar.javascript.lcov.reportPaths','sonar.scm.disabled','sonar.scm.provider','sonar.newCode.referenceBranch','sonar.newCode.period')
        $alcance = [ordered]@{}
        foreach ($linea in ($detalleTarea.task.scannerContext -split "`n")) {
            if ($linea -match '^\s*-?\s*([^=]+)=(.*)$') {
                $clave = $Matches[1].Trim(); $valor = $Matches[2].Trim()
                if ($clave -in $permitidas) { $alcance[$clave] = Proteger-Texto $valor }
            }
        }
        $resultado.scanner_scope = $alcance
    } catch { $resultado.scanner_scope_read = 'unavailable' }
    if ($resultado.compute_completed -and $resultado.analysis_id) {
        $gate = Consultar-Api "/api/qualitygates/project_status?analysisId=$($resultado.analysis_id)"
        $resultado.quality_gate = $gate.projectStatus.status
        $resultado.conditions = @($gate.projectStatus.conditions | Select-Object metricKey,status,actualValue,errorThreshold)
        $resultado.gate_period = $gate.projectStatus.period
        try { $resultado.new_code_definition = Consultar-Api "/api/new_code_periods/show?project=$proyecto" } catch { $resultado.new_code_definition_read = 'unavailable' }
        try {
            $historial = Consultar-Api "/api/project_analyses/search?project=$proyecto&ps=5"
            $resultado.analyses = @($historial.analyses | Select-Object key,date,revision,projectVersion)
            $resultado.current_snapshot_matches_analysis = $historial.analyses.Count -gt 0 -and $historial.analyses[0].key -eq $resultado.analysis_id
        } catch { $resultado.history_read = 'unavailable' }
        try {
            $metricas = 'bugs,vulnerabilities,code_smells,security_hotspots,duplicated_lines_density,coverage,line_coverage,branch_coverage,lines_to_cover,uncovered_lines,conditions_to_cover,uncovered_conditions,new_coverage,new_lines_to_cover,new_uncovered_lines,ncloc,files,ncloc_language_distribution'
            $medidas = Consultar-Api "/api/measures/component?component=$proyecto&metricKeys=$metricas"
            $resultado.measures = @($medidas.component.measures | Select-Object metric,value,period)
        } catch { $resultado.measures_read = 'unavailable' }
        $incidencias = Leer-Incidencias ''
        $resultado.issue_total = $incidencias.total
        $resultado.issue_export_complete = $incidencias.complete
        $resultado.issues = $incidencias.issues
        $resultado.priority_issues = @($incidencias.issues | Where-Object type -in @('BUG','VULNERABILITY'))
        $resultado.by_rule = @($incidencias.issues | Group-Object rule | Sort-Object Count -Descending | Select-Object Name,Count)
        $resultado.by_severity = @($incidencias.issues | Group-Object severity | Sort-Object Count -Descending | Select-Object Name,Count)
        $resultado.by_file = @($incidencias.issues | Group-Object component | Sort-Object Count -Descending | Select-Object Name,Count)
        try {
            $nuevas = Leer-Incidencias '&inNewCodePeriod=true'
            $resultado.new_issue_total = $nuevas.total
            $resultado.new_issues_export_complete = $nuevas.complete
            $resultado.new_issues = $nuevas.issues
        } catch { $resultado.new_issues_read = 'unavailable' }
        try {
            $archivos = @()
            for ($pagina=1; $pagina -le 20; $pagina++) {
                $arbol = Consultar-Api "/api/measures/component_tree?component=$proyecto&strategy=leaves&qualifiers=FIL&metricKeys=coverage,lines_to_cover,uncovered_lines&ps=500&p=$pagina"
                $archivos += @($arbol.components | Select-Object key,path,language,qualifier,measures)
                if ($archivos.Count -ge $arbol.paging.total) { break }
            }
            $resultado.file_measures = $archivos
            $resultado.file_export_complete = $archivos.Count -eq $arbol.paging.total
        } catch { $resultado.file_measures_read = 'unavailable' }
    }
    $resultado | ConvertTo-Json -Depth 14 | Set-Content -LiteralPath (Join-Path $destino 'resultado.json') -Encoding UTF8
    @{directory=$destino} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $raiz '.skilly-sonar-result.tmp') -Encoding UTF8
    Write-Output "Proyecto verificado: $proyecto; nombre: $($identidad.component.name)"
    Write-Output "Resultados locales sanitizados: $destino"
} finally {
    [Environment]::SetEnvironmentVariable('SONAR_TOKEN',$tokenAnterior,'Process')
    if ($puntero -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($puntero) }
    if ($null -ne $oculto) { $oculto.Dispose() }
    $tokenActual = $null
    $valoresPrivados = @()
}
