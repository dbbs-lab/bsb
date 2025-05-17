param (
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$repoName
)

if (-not $repoName) {
    Write-Error "Missing required repo name argument. Usage: .\devtools\migrate-issues.ps1 <repo-name>"
    exit 1
}

function Ensure-LabelExists {
    param (
        [string]$repo,
        [string]$label
    )

    $exists = gh label list --repo $repo --limit 1000 | Select-String -Pattern "^$label\s"
    if (-not $exists) {
        Write-Host "Creating label '$label' in $repo"
        gh label create $label --repo $repo --color "ededed" --description "Auto-created by migration script"
    }
}

# Set your repository names
$srcRepo = "dbbs-lab/$repoName"
$dstRepo = "dbbs-lab/bsb"
$label = "migrated"

Ensure-LabelExists -repo $dstRepo -label $label
Ensure-LabelExists -repo $dstRepo -label $repoName

# Get all open issues (excluding PRs)
$issuesJson = gh issue list --repo $srcRepo --state open --json number,title,body
$issues = $issuesJson | ConvertFrom-Json

foreach ($issue in $issues) {
    $number = $issue.number
    $title = $issue.title
    $body = $issue.body

    Write-Host "Migrating issue #${number}: $title"

    # Create issue in destination repo with reference back to source
    $newBody = "_Migrated from $srcRepo#${number}_`n`n---`n`n$body"
    # Create temp file
    $tempBodyFile = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempBodyFile -Encoding UTF8 -Value $newBody

        # Use --body-file instead of --body to avoid quoting issues
        $result = gh issue create `
            --repo $dstRepo `
            --title $title `
            --body-file $tempBodyFile `
            --label "$label,$repoName"
    }
    finally {
        # Cleanup temp file
        Remove-Item -Path $tempBodyFile -ErrorAction SilentlyContinue
    }

    if (-not $result) {
        Write-Host "❌ Failed to create issue for #$number."
        continue
    }

    Write-Host "Created in destination: $result"

    gh issue close $number --repo $srcRepo --comment "Moved to $result"
}
