# Testet die Shield-Radar-Vorlage (templates/radar) lokal mit Edge headless.
# Aufruf: powershell -File tests\radar\radar-test.ps1 [-Fall normal] [-Bild]   (Bilder landen in tests\radar\out)
# Fälle mit "erwartet_fehler": [n] prüfen, dass Slide n als Fehler gemeldet wird.
# Je Fall (faelle/*.json) und Slide: HTML bauen wie render.py, DOM nach JS prüfen (data-fertig / data-fehler), optional Screenshot.
param([string]$Fall = "*", [switch]$Bild)

$ErrorActionPreference = "Stop"
$hier = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $hier "..\..")).Path
$vorlage = Join-Path $repo "templates\radar\radar.html"
$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$profil = Join-Path $env:TEMP "es-radar-edgeprofil"
$utf8 = New-Object System.Text.UTF8Encoding($false)
function url($p) { "file:///" + ($p -replace '\\', '/' -replace ' ', '%20') }

if (-not (Test-Path $vorlage)) { Write-Output "FAIL: Vorlage fehlt ($vorlage)"; exit 1 }
$html0 = [IO.File]::ReadAllText($vorlage, $utf8)
New-Item -ItemType Directory -Force (Join-Path $hier "out") | Out-Null
$fehler = 0; $geprueft = 0

foreach ($datei in Get-ChildItem (Join-Path $hier "faelle\$Fall.json")) {
  $roh = [IO.File]::ReadAllText($datei.FullName, $utf8)
  $post = $roh | ConvertFrom-Json
  $n = @($post.slides).Count
  for ($i = 1; $i -le $n; $i++) {
    $vorl = @($post.slides)[$i - 1].vorlage
    $hoch = if ($vorl -eq "radar-story") { 1920 } else { 1350 }
    $daten = '{"seite": ' + $i + ', "logo": "' + (url "$repo\brand\logo.png") + '", "post": ' + $roh + '}'
    $daten = $daten.Replace("<", '\u003c')   # wie render.py: kein "<" roh im <script> (sonst bricht z. B. "<!--<script>" die Seite)
    $html = $html0.Replace("{{css}}", (url "$repo\templates\radar\radar.css")).Replace("{{js}}", (url "$repo\templates\radar\radar.js"))
    $html = $html.Replace("{{w}}", "1080").Replace("{{h}}", "$hoch").Replace("{{daten}}", $daten)
    $name = "$($datei.BaseName)-$i"
    $ziel = Join-Path $hier "out\$name.html"
    [IO.File]::WriteAllText($ziel, $html, $utf8)

    $dom = Join-Path $hier "out\$name.dom.txt"
    $a = @('--headless', '--disable-gpu', '--hide-scrollbars', "--user-data-dir=`"$profil`"", '--force-device-scale-factor=1',
           "--window-size=1080,$hoch", '--virtual-time-budget=15000', '--dump-dom', "`"$(url $ziel)`"")
    Start-Process -FilePath $edge -ArgumentList $a -Wait -NoNewWindow -RedirectStandardOutput $dom -RedirectStandardError (Join-Path $hier "out\edge.err")
    $txt = [IO.File]::ReadAllText($dom, $utf8)
    $ohneDaten = $txt -replace '(?s)<script type="application/json" id="daten">.*?</script>', ''
    $grund = @()
    if ($txt -notmatch 'data-fertig="ja"') { $grund += "nicht fertig" }
    $soll = @($post.erwartet_fehler) -contains $i
    if ($txt -match 'data-fehler="([^"]+)"') { if (-not $soll) { $grund += "fehler: $($Matches[1])" } } elseif ($soll) { $grund += "Fehler erwartet, aber nicht gemeldet" }
    if ($ohneDaten -match '<b>fett|<i>kursiv|<script>alert') { $grund += "HTML aus Text wurde ausgefuehrt" }
    $geprueft++
    if ($grund) { $fehler++; Write-Output "FAIL $name ($vorl): $($grund -join '; ')" } else { Write-Output "ok   $name ($vorl)" }

    if ($Bild) {
      $png = Join-Path $hier "out\$name.png"
      $b = @('--headless', '--disable-gpu', '--hide-scrollbars', "--user-data-dir=`"$profil`"", '--force-device-scale-factor=1',
             "--window-size=1080,$hoch", '--virtual-time-budget=15000', "--screenshot=`"$png`"", "`"$(url $ziel)`"")
      Start-Process -FilePath $edge -ArgumentList $b -Wait -NoNewWindow -RedirectStandardOutput (Join-Path $hier "out\edge.out") -RedirectStandardError (Join-Path $hier "out\edge.err")
    }
  }
}
Write-Output "$($geprueft - $fehler)/$geprueft ok"
if ($fehler) { exit 1 }
