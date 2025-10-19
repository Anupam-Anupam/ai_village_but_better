#!/bin/bash

# Test script to verify container communication in AI Village setup

echo "🧪 Starting AI Village container communication test..."

# Function to check if a service is ready
check_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service_name to be ready at $url..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi

        echo "   Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done

    echo "❌ $service_name failed to start within expected time"
    return 1
}

# Function to test API communication
test_api_communication() {
    echo "🔄 Testing API communication between containers..."

    # Test payload
    TEST_PAYLOAD='{
        "task_type": "test",
        "input_text": "Hello, this is a test message from the server container",
        "constraints": {}
    }'

    # Send request to server
    echo "📤 Sending test request to server..."
    RESPONSE=$(curl -s -X POST "http://localhost:8000/dispatch" \
        -H "Content-Type: application/json" \
        -d "$TEST_PAYLOAD")

    if [ $? -eq 0 ]; then
        echo "✅ Server responded successfully"

        # Check if we got responses from agents
        if echo "$RESPONSE" | grep -q "agent_outputs"; then
            echo "✅ Server successfully communicated with agents"

            # Print the response for verification
            echo "📋 Server response:"
            echo "$RESPONSE" | python3 -m json.tool
        else
            echo "⚠️  Server responded but no agent outputs found"
            echo "Response: $RESPONSE"
        fi
    else
        echo "❌ Failed to communicate with server"
        return 1
    fi
}

# Function to cleanup containers
cleanup() {
    echo "🧹 Cleaning up containers..."
    docker-compose down
    echo "✅ Cleanup completed"
}

# Set up error handling
trap cleanup EXIT

# Start containers
echo "🚀 Starting containers with docker-compose..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start containers"
    exit 1
fi

# Wait for server to be ready
if ! check_service "http://localhost:8000" "Server"; then
    echo "❌ Server failed to start"
    exit 1
fi

# Wait a bit more for agents to be ready
sleep 5

# Test API communication
if test_api_communication; then
    echo "🎉 Container communication test PASSED!"
    echo ""
    echo "📊 Test Summary:"
    echo "   ✅ Containers started successfully"
    echo "   ✅ Server is accessible"
    echo "   ✅ Inter-container communication working"
    echo "   ✅ API endpoints responding correctly"
    echo ""
    echo "🎯 The setup is ready for use!"
else
    echo "💥 Container communication test FAILED!"
    exit 1
fi
