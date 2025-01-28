$artifaces = '.\build', '.\dist'
foreach ($artifact in $artifaces) {
    if (Test-Path -Path $artifact) {
        Remove-Item -Path $artifact -Recurse -Force
    }
}
