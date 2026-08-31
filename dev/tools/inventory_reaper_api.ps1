param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot
)

$resolvedRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
Push-Location -LiteralPath $resolvedRoot
try {
    $relativeFiles = @(rg --files -g '*.lua' `
        -g '!dev/**' `
        -g '!_external_docs/**' `
        -g '!_old_stuff/**' `
        -g '!_future_ideas/**' `
        -g '!_raw_assets/**')
} finally {
    Pop-Location
}
$files = @($relativeFiles | ForEach-Object { Join-Path $resolvedRoot $_ })

$rows = foreach ($file in $files) {
    $matches = Select-String -LiteralPath $file -AllMatches `
        -Pattern '\b(?:r|reaper)\.([A-Za-z_][A-Za-z0-9_]*)\s*(?=\()'

    foreach ($line in $matches) {
        foreach ($match in $line.Matches) {
            $symbol = $match.Groups[1].Value
            $relativeFile = $file
            if ($file.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
                $relativeFile = $file.Substring($resolvedRoot.Length).TrimStart([char[]]'\/')
            }
            $provider = if ($symbol -like 'ImGui_*') {
                'ReaImGui'
            } elseif ($symbol -like 'CF_*') {
                'SWS'
            } elseif ($symbol -like 'JS_*') {
                'js_ReaScriptAPI'
            } else {
                'REAPER core'
            }

            [pscustomobject]@{
                Provider = $provider
                Symbol = $symbol
                File = $relativeFile
                Line = $line.LineNumber
            }
        }
    }
}

$rows |
    Group-Object Provider, Symbol |
    ForEach-Object {
        $first = $_.Group[0]
        [pscustomobject]@{
            Provider = $first.Provider
            Symbol = $first.Symbol
            References = $_.Count
            Files = ($_.Group.File | Sort-Object -Unique) -join '; '
        }
    } |
    Sort-Object Provider, Symbol |
    ConvertTo-Csv -NoTypeInformation
