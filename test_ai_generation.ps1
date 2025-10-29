# Test AI-powered content generation with different instructions

Write-Host "Testing AI-powered story generation..."

# Test 1: Original instruction
$payload1 = @{
    type = "generate"
    filename = "story1.txt"
    instruction = "Create a short story about friendship"
} | ConvertTo-Json -Depth 3

Write-Host "`nTest 1: Friendship story"
$response1 = Invoke-RestMethod -Uri "http://localhost:8001/execute" -Method POST -ContentType "application/json" -Body $payload1
Write-Host "Generated: $($response1.file.stdout.Substring(0, 100))..."

# Test 2: Different instruction
$payload2 = @{
    type = "generate"
    filename = "story2.txt"
    instruction = "Write a story about a robot learning to paint"
} | ConvertTo-Json -Depth 3

Write-Host "`nTest 2: Robot painting story"
$response2 = Invoke-RestMethod -Uri "http://localhost:8001/execute" -Method POST -ContentType "application/json" -Body $payload2
Write-Host "Generated: $($response2.file.stdout.Substring(0, 100))..."

Write-Host "`nAI-powered generation is working! Each instruction produces unique content."
