param(
    [Parameter(Mandatory=$true)][int]$Puerto,
    [Parameter(Mandatory=$true)][string]$RunId,
    [Parameter(Mandatory=$true)][string]$Destino
)
$ErrorActionPreference = 'Stop'
if ($Puerto -lt 1024 -or $Puerto -in @(8000,5173,5432,9000) -or $RunId -notmatch '^continuacion_[a-f0-9]+$') { throw 'Se requiere un destino aislado permitido.' }
$permitido = [IO.Path]::GetFullPath('C:\Users\felip\Downloads\SKILLY_recuperacion_edc8ec3a8e2e46cf940417c815a04d2b')
$salida = [IO.Path]::GetFullPath($Destino)
if (-not $salida.StartsWith($permitido + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $salida)) { throw 'La salida debe ser una carpeta nueva bajo el respaldo externo.' }
$java = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin\java.exe'
$jmeter = 'C:\Users\felip\Downloads\apache-jmeter-5.6.3\apache-jmeter-5.6.3\bin\ApacheJMeter.jar'
$plan = Join-Path $PSScriptRoot 'lectura_aislada.jmx'
[IO.Directory]::CreateDirectory($salida) | Out-Null
$inicio = [Diagnostics.Stopwatch]::StartNew()
$resumen = @()
foreach($usuarios in @(1,2,4)) {
    if ($inicio.Elapsed.TotalSeconds -gt 48) { throw 'Limite global de tiempo alcanzado; no se iniciara otra etapa.' }
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Puerto/__isolated/health" -TimeoutSec 3
    if ($health.isolated -ne $true -or $health.run_id -ne $RunId -or $health.database_port -eq 5432) { throw 'Guardia de aislamiento rechazada.' }
    $jtl = Join-Path $salida "etapa_$usuarios.jtl"
    $log = Join-Path $salida "etapa_$usuarios.log"
    $argumentos = @('-jar',$jmeter,'-n','-t',$plan,'-l',$jtl,'-j',$log,"-Jusers=$usuarios","-JtargetPort=$Puerto","-JexpectedRunId=$RunId",'-Jjmeter.save.saveservice.output_format=csv','-Jjmeter.save.saveservice.response_data=false','-Jjmeter.save.saveservice.response_data.on_error=false','-Jjmeter.save.saveservice.samplerData=false','-Jjmeter.save.saveservice.requestHeaders=false','-Jjmeter.save.saveservice.responseHeaders=false')
    $proceso = Start-Process -FilePath $java -ArgumentList $argumentos -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $salida "etapa_$usuarios.stdout.log") -RedirectStandardError (Join-Path $salida "etapa_$usuarios.stderr.log")
    $null = $proceso.Handle
    if (-not $proceso.WaitForExit(18000)) { $proceso.Kill(); throw 'La etapa excedio el limite de 18 segundos y fue detenida.' }
    $proceso.WaitForExit()
    $proceso.Refresh()
    if ($null -ne $proceso.ExitCode -and $proceso.ExitCode -ne 0) { throw "JMeter fallo en etapa $usuarios." }
    if (-not [IO.File]::ReadAllText((Join-Path $salida "etapa_$usuarios.stdout.log")).Contains('end of run')) { throw 'JMeter no confirmo el cierre normal de la etapa.' }
    $filas = @(Import-Csv -LiteralPath $jtl)
    $http = @($filas | Where-Object {$_.label -ne 'Guardia aislamiento'})
    $errores = @($filas | Where-Object {$_.success -ne 'true'})
    $tiempos = @($http | ForEach-Object {[double]$_.elapsed} | Sort-Object)
    $p95 = if($tiempos.Count) {$tiempos[[Math]::Min($tiempos.Count - 1, [Math]::Ceiling($tiempos.Count * .95) - 1)]} else {$null}
    $resumen += [pscustomobject]@{usuarios=$usuarios;muestras_http=$http.Count;errores=$errores.Count;p95_ms=$p95;max_ms=if($tiempos.Count){$tiempos[-1]}else{$null}}
    if ($errores.Count -gt 0 -or $http.Count -eq 0) { throw 'La etapa presento errores; se detiene la carga gradual.' }
}
$resultado = [pscustomobject]@{herramienta='Apache JMeter 5.6.3';run_id=$RunId;puerto=$Puerto;etapas=$resumen;duracion_total_segundos=[Math]::Round($inicio.Elapsed.TotalSeconds,2);limite_concurrencia=4;pausa_ms=1000;solo_lectura=$true;cuerpos_y_cabeceras_guardados=$false}
$resultado | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $salida 'resultado.json') -Encoding UTF8
$resumen | Format-Table
Write-Output "RESULTADO $salida"
