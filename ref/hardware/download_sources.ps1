$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $PSScriptRoot 'sources.json'
$manifest = Get-Content -LiteralPath $manifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
foreach ($source in $manifest.sources) {
  foreach ($artifact in $source.artifacts) {
    # Preserve pinned successful downloads. Retry unavailable sources only.
    if ($artifact.status -eq 'downloaded') { continue }
    $relativeTarget = if ($artifact.expected_path) { $artifact.expected_path } else { $artifact.path }
    $expectedKind = if ($artifact.expected_kind) { $artifact.expected_kind } else { $artifact.kind }
    $target = Join-Path $workspace $relativeTarget
    $incoming = $target + '.download'
    try {
      $response = Invoke-WebRequest -Uri $artifact.url -OutFile $incoming -UseBasicParsing -PassThru -TimeoutSec 40
      $bytes = [IO.File]::ReadAllBytes($incoming)
      $prefix = [Text.Encoding]::UTF8.GetString($bytes,0,[Math]::Min(2000,$bytes.Length))
      if ($expectedKind -eq 'pdf' -and -not $prefix.StartsWith('%PDF-')) { throw 'Downloaded content is not a PDF' }
      if ($expectedKind -eq 'html' -and ($bytes.Length -lt 1000 -or $prefix -match 'sgcaptcha|captcha/|challenge-platform')) { throw 'Downloaded HTML is a challenge/redirect, not source content' }
      Move-Item -LiteralPath $incoming -Destination $target -Force
      $artifact.path = $relativeTarget
      $artifact.kind = $expectedKind
      $artifact | Add-Member -NotePropertyName sha256 -NotePropertyValue (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -Force
      $artifact | Add-Member -NotePropertyName bytes -NotePropertyValue $bytes.Length -Force
      $artifact | Add-Member -NotePropertyName status -NotePropertyValue 'downloaded' -Force
      $artifact | Add-Member -NotePropertyName downloaded_on -NotePropertyValue (Get-Date -Format 'yyyy-MM-dd') -Force
      $artifact | Add-Member -NotePropertyName content_type -NotePropertyValue ([string]$response.Headers['Content-Type']) -Force
      $artifact.PSObject.Properties.Remove('error')
      Write-Output ($source.id + ' saved ' + $artifact.path + ' ' + $bytes.Length)
    } catch {
      $artifact | Add-Member -NotePropertyName status -NotePropertyValue 'download_failed' -Force
      $artifact | Add-Member -NotePropertyName error -NotePropertyValue $_.Exception.Message -Force
      if (Test-Path -LiteralPath $incoming) { Remove-Item -LiteralPath $incoming }
      Write-Output ($source.id + ' FAILED ' + $_.Exception.Message)
    }
  }
  $source.status = if (@($source.artifacts | Where-Object status -ne 'downloaded').Count -eq 0) {'downloaded'} else {'partial_or_unavailable'}
  $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}
