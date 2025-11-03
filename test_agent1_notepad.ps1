# Instruct agent1 to "open notepad" (emulated) by creating story.txt containing a short story.

# 1) Ask agent to generate a story and write it to story.txt
$generatePayload = @{
    type = "generate"
    filename = "story.txt"
    instruction = "Create a short, original story (3-6 sentences) about the agent exploring its sandbox and finding a surprising friendship. Return plain text suitable for a .txt file."
} | ConvertTo-Json -Depth 4

$genResp = Invoke-WebRequest -Method POST -Uri "http://localhost:8001/execute" -ContentType "application/json" -Body $generatePayload
Write-Host "Generate response: $($genResp.Content)"

# 2) Fetch the created file via the agent HTTP endpoint
try {
    $fileResp = Invoke-WebRequest -Method GET -Uri "http://localhost:8001/files/story.txt" -UseBasicParsing -TimeoutSec 10
    Write-Host "File content received:"
    Write-Host $fileResp.Content
} catch {
    Write-Host "Failed to fetch story.txt: $($_.Exception.Message)"
}

# 3) Get a screenshot of the file, save it locally, and open it
try {
    Write-Host "Requesting screenshot of story.txt..."
    $screenshotResp = Invoke-WebRequest -Method GET -Uri "http://localhost:8001/open/story.txt" -UseBasicParsing

    # Parse the JSON and get the base64 screenshot data
    $screenshotJson = $screenshotResp.Content | ConvertFrom-Json
    $base64String = $screenshotJson.screenshot

    # Decode the base64 string and save it to a file
    $outputFile = "story_screenshot.png"
    $bytes = [System.Convert]::FromBase64String($base64String)
    [System.IO.File]::WriteAllBytes($outputFile, $bytes)

    Write-Host "Success! Screenshot saved to '$outputFile' and is being opened."
    Invoke-Item $outputFile
} catch {
    Write-Host "Failed to get or open screenshot: $($_.Exception.Message)"
}
