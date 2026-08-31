param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$ProbeResults
)

$probePath = (Resolve-Path -LiteralPath $ProbeResults).Path
$inventoryScript = Join-Path $PSScriptRoot 'inventory_reaper_api.ps1'
$inventory = @(& $inventoryScript -SourceRoot $SourceRoot | ConvertFrom-Csv)

$availability = @{}
Get-Content -LiteralPath $probePath | ForEach-Object {
    if ($_ -match '^(RPR_[A-Za-z_][A-Za-z0-9_]*)\s+(YES|NO)$') {
        $availability[$matches[1].Substring(4)] = $matches[2]
    }
}

$inventory |
    ForEach-Object {
        $status = if ($_.Provider -eq 'REAPER core') {
            if ($availability.ContainsKey($_.Symbol)) {
                $availability[$_.Symbol]
            } else {
                'NOT_PROBED'
            }
        } else {
            'OUT_OF_SCOPE'
        }

        [pscustomobject]@{
            Provider = $_.Provider
            Symbol = $_.Symbol
            Reaper420Direct = $status
            References = $_.References
            Files = $_.Files
        }
    } |
    Sort-Object Provider, Symbol |
    ConvertTo-Csv -NoTypeInformation
