# Testet die Behind-the-Shield-Vorlage (templates/bts) lokal mit Edge headless.
# Aufruf: powershell -File tests\bts\bts-test.ps1 [-Fall normal] [-Bild]   (Bilder landen in tests\bts\out)
# Eine echte Folge testen: -Post <Ordner mit post.json und Fotos>; nichts wird in versionierte Ordner kopiert, nur nach out\.
# Fälle mit "erwartet_fehler": [n] prüfen, dass Slide n als Fehler gemeldet wird.
# Je Fall (faelle/*.json) und Slide: HTML bauen wie render.py, DOM nach JS prüfen (data-fertig / data-fehler), optional Screenshot.
[CmdletBinding()]
param([string]$Fall = "*", [switch]$Bild, [string]$Post)

$ErrorActionPreference = "Stop"
$hier = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $hier "..\..")).Path
$vorlage = Join-Path $repo "templates\bts\bts.html"
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$profil = Join-Path $env:TEMP "es-bts-edgeprofil"
$utf8 = New-Object System.Text.UTF8Encoding($false)
function url($p) { "file:///" + ($p -replace '\\', '/' -replace ' ', '%20') }
# Ein neuer Edge mit demselben Profil hängt sich sonst an einen noch laufenden an und liefert nichts (Fotos dauern länger als beim Radar)
function warteAufEdge {
  for ($i = 0; $i -lt 60; $i++) {
    # nur der Haupt-Prozess (ohne --type=) hält das Profil; Hilfsprozesse wie crashpad laufen länger und stören nicht
    if (-not (Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object { $_.CommandLine -match [regex]::Escape($profil) -and $_.CommandLine -notmatch '--type=' })) { return }
    Start-Sleep -Milliseconds 250
  }
}

if (-not (Test-Path $vorlage)) { Write-Output "FAIL: Vorlage fehlt ($vorlage)"; exit 1 }
$html0 = [IO.File]::ReadAllText($vorlage, $utf8)
$out = Join-Path $hier "out"
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item (Join-Path $hier "fotos\*") $out -Force   # Bildpfade in den Fällen sind relativ zur HTML-Datei
$postOrdner = $Post
if ($postOrdner) {
  if (-not (Test-Path (Join-Path $postOrdner "post.json"))) { Write-Output "FAIL: keine post.json in $postOrdner"; exit 1 }
  Get-ChildItem $postOrdner -File | Where-Object { $_.Extension -match '^\.(jpe?g|png)$' } | Copy-Item -Destination $out -Force
  $faelle = @(Get-Item (Join-Path $postOrdner "post.json"))
} else {
  $faelle = Get-ChildItem (Join-Path $hier "faelle\$Fall.json")
}
$fehler = 0; $geprueft = 0

foreach ($datei in $faelle) {
  $roh = [IO.File]::ReadAllText($datei.FullName, $utf8)
  $fallDaten = $roh | ConvertFrom-Json
  $n = @($fallDaten.slides).Count
  for ($i = 1; $i -le $n; $i++) {
    $vorl = @($fallDaten.slides)[$i - 1].vorlage
    $daten = '{"seite": ' + $i + ', "logo": "' + (url "$repo\brand\logo.png") + '", "post": ' + $roh + '}'
    $daten = $daten.Replace("<", '\u003c')   # wie render.py: kein "<" roh im <script>
    $html = $html0.Replace("{{css}}", (url "$repo\templates\bts\bts.css")).Replace("{{js}}", (url "$repo\templates\bts\bts.js"))
    $html = $html.Replace("{{w}}", "1080").Replace("{{h}}", "1350").Replace("{{daten}}", $daten)
    $name = "$(if ($postOrdner) { Split-Path $postOrdner -Leaf } else { $datei.BaseName })-$i"
    $ziel = Join-Path $out "$name.html"
    [IO.File]::WriteAllText($ziel, $html, $utf8)

    $dom = Join-Path $out "$name.dom.txt"
    $a = @('--headless', '--disable-gpu', '--hide-scrollbars', "--user-data-dir=`"$profil`"", '--force-device-scale-factor=1',
           '--window-size=1080,1350', '--virtual-time-budget=15000', '--allow-file-access-from-files', '--dump-dom', "`"$(url $ziel)`"")
    warteAufEdge
    Start-Process -FilePath $edge -ArgumentList $a -Wait -NoNewWindow -RedirectStandardOutput $dom -RedirectStandardError (Join-Path $out "edge.err")
    $txt = [IO.File]::ReadAllText($dom, $utf8)
    $ohneDaten = $txt -replace '(?s)<script type="application/json" id="daten">.*?</script>', ''
    $grund = @()
    if ($txt -notmatch 'data-fertig="ja"') { $grund += "nicht fertig" }
    $soll = @($fallDaten.erwartet_fehler) -contains $i
    if ($txt -match 'data-fehler="([^"]+)"') { if (-not $soll) { $grund += "fehler: $($Matches[1])" } } elseif ($soll) { $grund += "Fehler erwartet, aber nicht gemeldet" }
    if ($ohneDaten -match '<b>fett|<i>kursiv|<script>alert') { $grund += "HTML aus Text wurde ausgefuehrt" }
    if ($ohneDaten -match '[!?…]\.<') { $grund += "Satzzeichen doppelt (z. B. !.)" }
    $ankuendigung = @($fallDaten.slides)[$i - 1].ankuendigung -eq $true
    if ($vorl -eq 'bts-bastion' -and $ankuendigung -and $ohneDaten -notmatch 'ab 18 Jahren') { $grund += "Altersangabe nicht eindeutig (ab 18 Jahren)" }
    # Ohne Ankündigung kein Termin, Ort oder Einlass (30.1. ist bis zum Save the Date geheim)
    if ($vorl -eq 'bts-bastion' -and -not $ankuendigung -and $ohneDaten -cmatch '30\.0?1\.|Abendkasse|Club Bastion|120 Pl') { $grund += "Termin oder Ort ohne Ankuendigung" }
    $geprueft++
    $info = if ($soll -and $txt -match 'data-fehler="([^"]+)"') { " [erwartet: $($Matches[1])]" } else { "" }
    if ($grund) { $fehler++; Write-Output "FAIL $name ($vorl): $($grund -join '; ')" } else { Write-Output "ok   $name ($vorl)$info" }

    if ($Bild) {
      $png = Join-Path $out "$name.png"
      $b = @('--headless', '--disable-gpu', '--hide-scrollbars', "--user-data-dir=`"$profil`"", '--force-device-scale-factor=1',
             '--window-size=1080,1350', '--virtual-time-budget=15000', '--allow-file-access-from-files', "--screenshot=`"$png`"", "`"$(url $ziel)`"")
      warteAufEdge
      Start-Process -FilePath $edge -ArgumentList $b -Wait -NoNewWindow -RedirectStandardOutput (Join-Path $out "edge.out") -RedirectStandardError (Join-Path $out "edge.err")
    }
  }
}
Write-Output "$($geprueft - $fehler)/$geprueft ok"
if ($fehler) { exit 1 }
