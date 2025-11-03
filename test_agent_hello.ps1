# Instruct the agent to generate a Python script that prints "hello world", then fetch it back.

# 1) Generate file by instruction
$generatePayload = @{
    type = "generate"
    filename = "hello.py"
    instruction = "Create a Python script that prints 'hello world'."
} | ConvertTo-Json -Depth 3
$genResp = Invoke-WebRequest -Method POST -Uri "http://localhost:8001/execute" -ContentType "application/json" -Body $generatePayload
Write-Host "Generate response: $($genResp.Content)"

# 2) Read file back using cat via shell command
$catPayload = @{
    type = "shell"
    command = "cat hello.py"
} | ConvertTo-Json -Depth 2
$catResp = Invoke-WebRequest -Method POST -Uri "http://localhost:8001/execute" -ContentType "application/json" -Body $catPayload
Write-Host "Cat response: $($catResp.Content)"
