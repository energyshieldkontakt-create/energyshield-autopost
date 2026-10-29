# Mac-Variante der Messung in helligkeit.ps1 (Automatisierung/mac/PORTIERUNG.md, Werkzeug 5): ffmpeg statt System.Drawing.
# Gleiche Messung: mittlere Helligkeit (0,2126 R + 0,7152 G + 0,0722 B) jedes 5. Pixels in x 320–760, y 340–800.
. (Join-Path $hier "..\..\..\Automatisierung\mac\werkzeuge.ps1")
function mittelMac($pfad) {
  $roh = Join-Path $MacTemp "es-helligkeit.rgb"
  & $MacFfmpeg -v error -y -i $pfad -vf "crop=440:460:320:340,format=rgb24" -f rawvideo $roh
  if ($LASTEXITCODE) { throw "ffmpeg kann $pfad nicht lesen" }
  $b = [IO.File]::ReadAllBytes($roh)
  $summe = 0; $n = 0
  for ($x = 0; $x -lt 440; $x += 5) { for ($y = 0; $y -lt 460; $y += 5) {
    $i = ($y * 440 + $x) * 3; $summe += 0.2126 * $b[$i] + 0.7152 * $b[$i + 1] + 0.0722 * $b[$i + 2]; $n++ } }
  return $summe / $n
}
