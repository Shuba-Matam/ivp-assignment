param(
    [Parameter(Mandatory=$true)][string]$InputDocx,
    [Parameter(Mandatory=$true)][string]$OutputPdf
)
$ErrorActionPreference = 'Stop'
$taskWord = $null
$taskDoc = $null
try {
    $taskWord = New-Object -ComObject Word.Application
    $taskWord.Visible = $false
    $taskWord.DisplayAlerts = 0
    $taskWord.AutomationSecurity = 3
    $taskDoc = $taskWord.Documents.Open($InputDocx, $false, $true, $false)
    $taskDoc.Repaginate()
    $taskDoc.ExportAsFixedFormat($OutputPdf, 17)
    Write-Output ('Exported PDF; pages: ' + $taskDoc.ComputeStatistics(2))
} finally {
    if ($null -ne $taskDoc) { $taskDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskDoc) }
    if ($null -ne $taskWord) { $taskWord.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskWord) }
}
