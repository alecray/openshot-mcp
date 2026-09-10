# protect-files.ps1 — PreToolUse guard for Edit/Write/NotebookEdit.
#
# Why PowerShell (not .sh/jq): .claude/hooks run through the OS, and bash/jq are not
# guaranteed on Windows. .githooks/* are different — those run through Git's bundled sh.
#
# Reads the tool-input JSON from stdin, extracts the target file path, and blocks
# (exit 2) edits to protected paths. Exit 2 tells Claude Code to deny the tool call
# and surface the stderr message.

$ErrorActionPreference = 'Stop'

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
    $payload = $raw | ConvertFrom-Json
} catch {
    # If we can't parse input, don't block the user.
    exit 0
}

$filePath = $payload.tool_input.file_path
if ([string]::IsNullOrWhiteSpace($filePath)) { exit 0 }

# Normalize to forward slashes for matching.
$norm = ($filePath -replace '\\', '/')

# Protected patterns (regex, case-insensitive).
$protected = @(
    '(^|/)\.env($|\.)',       # .env, .env.local, .env.production ...
    '(^|/)docs/DESIGN\.md$',
    '(^|/)legacy/',
    '(^|/)generated/'
)

foreach ($pattern in $protected) {
    if ($norm -imatch $pattern) {
        [Console]::Error.WriteLine("BLOCKED: '$filePath' is a protected path. Ask the user before modifying it (see CLAUDE.md > Protected paths).")
        exit 2
    }
}

exit 0
