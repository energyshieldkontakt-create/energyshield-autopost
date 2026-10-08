# Baut eine Behind-the-Shield-Folge lokal fertig (Windows, ohne ffmpeg):
#  1. prüft und rendert alle Slides mit bts-test.ps1 (Bilder in tests\bts\out),
#  2. setzt bei bts-produktion das Visualizer-Video ("visualizer") samt Ton in den 9:16-Rahmen und speichert das
#     fertige MP4 (1080 x 1350, H.264/AAC, höchstens 18 MB) als "video" im Entwurfsordner (Windows Media Editing),
#  3. legt den fertigen Beitrag zum Ansehen und Weiterschicken in <Ordner>\fertig\ ab: 1.jpg, 2.jpg …, die
#     Video-Slide als <n>.mp4, dazu caption.txt.
# Aufruf: powershell -NoProfile -ExecutionPolicy Bypass -File tests\bts\bts-fertig.ps1 -Post ..\Content\Behind-the-Shield\<Resident>
# -Sek 5 baut zum schnellen Testen nur die ersten 5 Sekunden des Videos.
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Post, [double]$Sek = 0)

$ErrorActionPreference = "Stop"
$hier = $PSScriptRoot
$Post = (Resolve-Path $Post).Path
$utf8 = New-Object System.Text.UTF8Encoding($false)
$MAX_MB = 18   # wie MAX_VIDEO_MB in scripts/render.py: jsDelivr liefert nur Dateien bis ca. 20 MB aus
function stopp($text) { Write-Output "FAIL: $text"; exit 1 }

# 1. Slides prüfen und rendern (eigener Prozess, weil bts-test.ps1 mit exit endet)
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $hier "bts-test.ps1") -Post $Post -Bild
if ($LASTEXITCODE) { stopp "Slides melden Fehler, kein fertiger Beitrag" }

# Windows-Media-Schnittstellen (WinRT) für PowerShell 5.1; Listen nur über das .NET-Interface befüllbar
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFolder, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Editing.MediaComposition, Windows.Media.Editing, ContentType = WindowsRuntime]
$null = [Windows.Media.Editing.MediaClip, Windows.Media.Editing, ContentType = WindowsRuntime]
$null = [Windows.Media.Editing.MediaOverlay, Windows.Media.Editing, ContentType = WindowsRuntime]
$null = [Windows.Media.Editing.MediaOverlayLayer, Windows.Media.Editing, ContentType = WindowsRuntime]
$null = [Windows.Media.MediaProperties.MediaEncodingProfile, Windows.Media.MediaProperties, ContentType = WindowsRuntime]
$null = [Windows.Media.Transcoding.TranscodeFailureReason, Windows.Media.Transcoding, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.ImageStream, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$methoden = [System.WindowsRuntimeSystemExtensions].GetMethods()
$alsTask = $methoden | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$alsTaskFortschritt = $methoden | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperationWithProgress`2' } | Select-Object -First 1
function warte($op, [Type]$typ) { $t = $alsTask.MakeGenericMethod($typ).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
function fuegeAn($liste, $wert, [Type]$typ) {
  [System.Collections.Generic.ICollection`1].MakeGenericType($typ).GetMethod("Add").Invoke($liste, @($wert.psobject.BaseObject)) | Out-Null
}
function datei($pfad) { warte ([Windows.Storage.StorageFile]::GetFileFromPathAsync($pfad)) ([Windows.Storage.StorageFile]) }
function clip($pfad) { warte ([Windows.Media.Editing.MediaClip]::CreateFromFileAsync((datei $pfad))) ([Windows.Media.Editing.MediaClip]) }

# Grafik (PNG) als Hintergrund, Video als Ebene in der Innenfläche des Rahmens, Ton des Videos
function setzeVideo($grafik, $quelle, $ziel, $x, $y, $b, $h) {
  $video = clip $quelle
  $dauer = $video.OriginalDuration
  if ($Sek -gt 0 -and $Sek -lt $dauer.TotalSeconds) { $video.TrimTimeFromEnd = $dauer - [TimeSpan]::FromSeconds($Sek); $dauer = [TimeSpan]::FromSeconds($Sek) }
  if ($dauer.TotalSeconds -lt 3 -or $dauer.TotalSeconds -gt 60) { stopp "Video muss 3 bis 60 Sekunden lang sein (ist $([int]$dauer.TotalSeconds) s)" }
  if ($video.EmbeddedAudioTracks.Count -lt 1) { stopp "Visualizer-Video hat keinen Ton" }
  $hintergrund = warte ([Windows.Media.Editing.MediaClip]::CreateFromImageFileAsync((datei $grafik), $dauer)) ([Windows.Media.Editing.MediaClip])
  $komp = New-Object Windows.Media.Editing.MediaComposition
  fuegeAn $komp.Clips $hintergrund ([Windows.Media.Editing.MediaClip])
  $ebene = New-Object Windows.Media.Editing.MediaOverlay -ArgumentList $video
  $ebene.Position = New-Object Windows.Foundation.Rect -ArgumentList $x, $y, $b, $h
  $ebene.AudioEnabled = $true
  $stapel = New-Object Windows.Media.Editing.MediaOverlayLayer
  fuegeAn $stapel.Overlays $ebene ([Windows.Media.Editing.MediaOverlay])
  fuegeAn $komp.OverlayLayers $stapel ([Windows.Media.Editing.MediaOverlayLayer])

  $profil = [Windows.Media.MediaProperties.MediaEncodingProfile]::CreateMp4([Windows.Media.MediaProperties.VideoEncodingQuality]::HD1080p)
  $kbps = [math]::Min(4000, [int]($MAX_MB * 8192 / $dauer.TotalSeconds) - 400)   # Reserve für Ton und Schwankungen des Encoders
  $profil.Video.Width = 1080; $profil.Video.Height = 1350; $profil.Video.Bitrate = $kbps * 1000
  $profil.Video.FrameRate.Numerator = 30; $profil.Video.FrameRate.Denominator = 1
  $profil.Audio.SampleRate = 48000; $profil.Audio.ChannelCount = 2; $profil.Audio.Bitrate = 192000

  $ordner = warte ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync((Split-Path $ziel))) ([Windows.Storage.StorageFolder])
  $datei = warte ($ordner.CreateFileAsync((Split-Path $ziel -Leaf), [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
  $op = $komp.RenderToFileAsync($datei, [Windows.Media.Editing.MediaTrimmingPreference]::Precise, $profil)
  $t = $alsTaskFortschritt.MakeGenericMethod([Windows.Media.Transcoding.TranscodeFailureReason], [double]).Invoke($null, @($op))
  $t.Wait(-1) | Out-Null
  if ("$($t.Result)" -ne "None") { stopp "Video-Einbau fehlgeschlagen: $($t.Result)" }
}

# Prüft das fertige Video wie render.py (Größe, Format, Ton) und speichert ein Standbild zur Kontrolle
function pruefeVideo($pfad, $standbild) {
  $mb = (Get-Item $pfad).Length / 1MB
  if ($mb -gt $MAX_MB) { stopp ("Video ist {0:N1} MB groß, maximal $MAX_MB MB möglich" -f $mb) }
  $c = clip $pfad
  $v = $c.GetVideoEncodingProperties()
  if ($v.Width -ne 1080 -or $v.Height -ne 1350) { stopp "Video hat $($v.Width) x $($v.Height) statt 1080 x 1350" }
  if ($c.EmbeddedAudioTracks.Count -lt 1) { stopp "Fertiges Video hat keinen Ton" }
  $komp = New-Object Windows.Media.Editing.MediaComposition
  fuegeAn $komp.Clips $c ([Windows.Media.Editing.MediaClip])
  $sek = [math]::Min(10, $c.OriginalDuration.TotalSeconds / 2)
  $bild = warte ($komp.GetThumbnailAsync([TimeSpan]::FromSeconds($sek), 0, 0, [Windows.Media.Editing.VideoFramePrecision]::NearestFrame)) ([Windows.Graphics.Imaging.ImageStream])
  $ein = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($bild)
  $aus = [IO.File]::Create($standbild); $ein.CopyTo($aus); $aus.Close(); $ein.Close()
  "{0:N1} MB, {1} x {2}, {3:N1} s, Ton ok" -f $mb, $v.Width, $v.Height, $c.OriginalDuration.TotalSeconds
}

$roh = [IO.File]::ReadAllText((Join-Path $Post "post.json"), $utf8)
$daten = $roh | ConvertFrom-Json
$slides = @($daten.slides)
$name = Split-Path $Post -Leaf
$out = Join-Path $hier "out"
$fertig = Join-Path $Post "fertig"
New-Item -ItemType Directory -Force $fertig | Out-Null
Get-ChildItem $fertig -File | Where-Object { $_.Name -match '^\d+\.(jpg|mp4)$' -or $_.Name -eq 'caption.txt' } | Remove-Item
$jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$qualitaet = New-Object System.Drawing.Imaging.EncoderParameters 1
$qualitaet.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), ([long]92)

for ($i = 1; $i -le $slides.Count; $i++) {
  $s = $slides[$i - 1]
  $png = Join-Path $out "$name-$i.png"
  if ($s.vorlage -ne 'bts-produktion') {   # wie render.py: Bilder als JPEG (Qualität 92)
    $bild = [System.Drawing.Image]::FromFile($png)
    $bild.Save((Join-Path $fertig "$i.jpg"), $jpeg, $qualitaet)
    $bild.Dispose()
    continue
  }
  if (-not $s.visualizer) { stopp "bts-produktion: Feld ""visualizer"" (Video aus TouchDesigner im Entwurfsordner) fehlt" }
  if (-not ($s.video -match '^[^\\/]+\.mp4$')) { stopp "bts-produktion: Feld ""video"" (Dateiname des fertigen MP4, z. B. produktion.mp4) fehlt" }
  $quelle = Join-Path $Post $s.visualizer
  if (-not (Test-Path -LiteralPath $quelle)) { stopp "Visualizer-Video '$($s.visualizer)' fehlt im Entwurfsordner" }
  $dom = [IO.File]::ReadAllText((Join-Path $out "$name-$i.dom.txt"), $utf8)
  if ($dom -notmatch 'data-video="(\d+),(\d+),(\d+),(\d+)"') { stopp "Rahmen für das Video nicht gefunden (data-video fehlt)" }
  $r = $Matches
  $ziel = Join-Path $Post $s.video
  Write-Output "Video-Slide $i`: setze '$($s.visualizer)' in den Rahmen ($($r[3]) x $($r[4]) bei $($r[1]), $($r[2])) …"
  setzeVideo $png $quelle $ziel ([double]$r[1]) ([double]$r[2]) ([double]$r[3]) ([double]$r[4])
  Write-Output ("ok   Video-Slide $i`: " + (pruefeVideo $ziel (Join-Path $out "$name-$i-video.jpg")))
  Copy-Item $ziel (Join-Path $fertig "$i.mp4")
}
if ($daten.caption) { [IO.File]::WriteAllText((Join-Path $fertig "caption.txt"), [string]$daten.caption, $utf8) }
Write-Output "Fertiger Beitrag: $fertig"
