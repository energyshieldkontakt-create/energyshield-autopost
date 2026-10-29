# Mac-Variante der Windows-Teile von bts-fertig.ps1 (Automatisierung/mac/PORTIERUNG.md, Werkzeug 2):
# ffmpeg statt Windows Media Editing, sips statt System.Drawing. bts-fertig.ps1 lädt diese Datei nur unter macOS
# (pwsh 7) und ruft dann setzeVideoMac, pruefeVideoMac und speichereJpegMac statt der Windows-Funktionen.
# Gleiches Ergebnis wie unter Windows: Grafik als Hintergrund, Video in der Innenfläche des Rahmens, Ton des Videos,
# 1080 x 1350, 30 fps, H.264/AAC.
. (Join-Path $hier "..\..\..\Automatisierung\mac\werkzeuge.ps1")
$inv = [Globalization.CultureInfo]::InvariantCulture

function ffprobeJson($pfad) { (& $MacFfprobe -v error -show_entries "stream=codec_type,width,height:format=duration" -of json $pfad | Out-String) | ConvertFrom-Json }

function setzeVideoMac($grafik, $quelle, $ziel, $x, $y, $b, $h) {
  $j = ffprobeJson $quelle
  $dauer = [double]::Parse($j.format.duration, $inv)
  if ($Sek -gt 0 -and $Sek -lt $dauer) { $dauer = $Sek }
  if ($dauer -lt 3 -or $dauer -gt 60) { stopp "Video muss 3 bis 60 Sekunden lang sein (ist $([int]$dauer) s)" }
  if (-not ($j.streams | Where-Object codec_type -eq 'audio')) { stopp "Visualizer-Video hat keinen Ton" }
  $kbps = [math]::Min(4000, [int]($MAX_MB * 8192 / $dauer) - 400)   # wie unter Windows: Reserve für Ton und Encoder
  # Video wie MediaOverlay genau auf die Rahmenfläche skaliert; Bild in BT.709 (Kennung wie bei den Blend-Reels)
  $filter = "[1:v]fps=30,scale=$([int]$b):$([int]$h):flags=lanczos,setsar=1[v];[0:v][v]overlay=$([int]$x):$([int]$y):eof_action=pass,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[bild]"
  & $MacFfmpeg -hide_banner -loglevel error -y -loop 1 -framerate 30 -i $grafik -i $quelle -filter_complex $filter -map '[bild]' -map 1:a:0 `
    -t $dauer.ToString('0.###', $inv) -r 30 -c:v libx264 -preset slow -b:v "$($kbps)k" -maxrate "$($kbps)k" -bufsize "$(2 * $kbps)k" `
    -colorspace bt709 -color_primaries bt709 -color_trc bt709 -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart $ziel
  if ($LASTEXITCODE) { stopp "Video-Einbau fehlgeschlagen (ffmpeg)" }
}

# Prüft das fertige Video wie render.py (Größe, Format, Ton) und speichert ein Standbild zur Kontrolle
function pruefeVideoMac($pfad, $standbild) {
  $mb = (Get-Item $pfad).Length / 1MB
  if ($mb -gt $MAX_MB) { stopp ("Video ist {0:N1} MB groß, maximal $MAX_MB MB möglich" -f $mb) }
  $j = ffprobeJson $pfad
  $v = $j.streams | Where-Object codec_type -eq 'video' | Select-Object -First 1
  if ($v.width -ne 1080 -or $v.height -ne 1350) { stopp "Video hat $($v.width) x $($v.height) statt 1080 x 1350" }
  if (-not ($j.streams | Where-Object codec_type -eq 'audio')) { stopp "Fertiges Video hat keinen Ton" }
  $dauer = [double]::Parse($j.format.duration, $inv)
  $sek = [math]::Min(10, $dauer / 2)
  & $MacFfmpeg -hide_banner -loglevel error -y -ss $sek.ToString('0.###', $inv) -i $pfad -frames:v 1 -q:v 2 $standbild
  "{0:N1} MB, {1} x {2}, {3:N1} s, Ton ok" -f $mb, $v.width, $v.height, $dauer
}

# PNG als JPEG mit Qualität 92 (wie render.py und System.Drawing unter Windows)
function speichereJpegMac($png, $jpg) {
  $null = & /usr/bin/sips -s format jpeg -s formatOptions 92 $png --out $jpg
  if ($LASTEXITCODE -or -not (Test-Path -LiteralPath $jpg)) { stopp "JPEG aus $png nicht erzeugt (sips)" }
}
