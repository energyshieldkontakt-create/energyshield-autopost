# Prüft, dass die Einfärbung des Cover-Fotos so dunkel ist wie im freigegebenen Muster 1B.
# Misst die mittlere Helligkeit im Schild (x 320–760, y 340–800), wo das Foto nicht abgedunkelt ist, in out\normal-1.png und im Muster.
# Aufruf (nach bts-test.ps1 -Fall normal -Bild): powershell -File tests\bts\helligkeit.ps1
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$hier = $PSScriptRoot
function mittel($pfad) {
  $b = [System.Drawing.Bitmap]::FromFile($pfad)
  $summe = 0; $n = 0
  for ($x = 320; $x -lt 760; $x += 5) { for ($y = 340; $y -lt 800; $y += 5) {
    $c = $b.GetPixel($x, $y); $summe += 0.2126 * $c.R + 0.7152 * $c.G + 0.0722 * $c.B; $n++ } }
  $b.Dispose(); return $summe / $n
}
$muster = mittel (Join-Path $hier "..\..\..\Automatisierung\behind-the-shield-entwurf\1B-cover-eingefaerbt.png")
$render = mittel (Join-Path $hier "out\normal-1.png")
$abw = [math]::Abs($render - $muster) / $muster
"Muster {0:N1} · Render {1:N1} · Abweichung {2:P0}" -f $muster, $render, $abw
if ($abw -gt 0.15) { "FAIL: Einfärbung weicht mehr als 15 % vom Muster ab"; exit 1 } else { "ok" }
