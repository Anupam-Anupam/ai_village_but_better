#!/bin/bash
# Complete Build, Run, and Test Script
# =====================================
# Run this script to build, start, and test the full storage implementation

set -e  # Exit on error

echo "========================================"
echo "Storage Implementation: Complete Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Install Python Dependencies
echo -e "${YELLOW}[Step 1/10] Installing Python dependencies...${NC}"
if [ -f "storage/requirements.txt" ]; then
    pip install -r storage/requirements.txt
    pip install httpx asyncio 2>/dev/null || true
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}✗ storage/requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Step 2: Check Docker Compose
echo -e "${YELLOW}[Step 2/10] Checking Docker Compose configuration...${NC}"
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗ docker-compose.yml not found${NC}"
    exit 1
fi

# Check if MinIO service exists
if ! grep -q "minio:" docker-compose.yml; then
    echo -e "${YELLOW}⚠ MinIO service not found in docker-compose.yml${NC}"
    echo "Please add MinIO service to docker-compose.yml (see QUICKSTART.md)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Docker Compose configuration found${NC}"
fi
echo ""

# Step 3: Build Docker Images
echo -e "${YELLOW}[Step 3/10] Building Docker images...${NC}"
docker-compose build
echo -e "${GREEN}✓ Docker images built${NC}"
echo ""

# Step 4: Start Database Services
echo -e "${YELLOW}[Step 4/10] Starting database services...${NC}"
docker-compose up -d postgres mongodb
if docker-compose ps | grep -q "minio"; then
    docker-compose up -d minio
fi
echo "Waiting for databases to initialize (10 seconds)..."
sleep 10
echo -e "${GREEN}✓ Database services started${NC}"
echo ""

# Step 5: Verify Database Services
echo -e "${YELLOW}[Step 5/10] Verifying database services...${NC}"

# Check PostgreSQL
if docker exec postgres pg_isready -U hub > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready${NC}"
    exit 1
fi

# Check MongoDB
if docker exec mongodb mongosh -u admin -p password --authenticationDatabase admin --quiet --eval "db.runCommand({ ping: 1 })" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MongoDB is ready${NC}"
else
    echo -e "${RED}✗ MongoDB is not ready${NC}"
    exit 1
fi

# Check MinIO if it exists
if docker-compose ps | grep -q "minio"; then
    if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MinIO is ready${NC}"
    else
        echo -e "${YELLOW}⚠ MinIO health check failed (may still be starting)${NC}"
    fi
fi
echo ""

# Step 6: Start Application Services
echo -e "${YELLOW}[Step 6/10] Starting application services...${NC}"
docker-compose up -d agent1 server
sleep 5
echo -e "${GREEN}✓ Application services started${NC}"
echo ""

# Step 7: Verify Application Services
echo -e "${YELLOW}[Step 7/10] Verifying application services...${NC}"

# Check Agent
if curl -s http://localhost:8001/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Agent is running${NC}"
else
    echo -e "${YELLOW}⚠ Agent may still be starting${NC}"
fi

# Check Server
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${YELLOW}⚠ Server may still be starting${NC}"
fi
echo ""

# Step 8: Set Environment Variables
echo -e "${YELLOW}[Step 8/10] Setting environment variables...${NC}"
export AGENT_ID=agent1
export MONGODB_URL=mongodb://admin:password@localhost:27017/agent1db?authSource=admin
export POSTGRES_URL=postgresql://hub:hubpassword@localhost:5432/hub
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export AGENT_URL=http://localhost:8001
export SERVER_URL=http://localhost:8000
echo -e "${GREEN}✓ Environment variables set${NC}"
echo ""

# Step 9: Run Simple Storage Tests
echo -e "${YELLOW}[Step 9/10] Running simple storage tests...${NC}"
if python test_storage_simple.py; then
    echo -e "${GREEN}✓ Simple storage tests passed${NC}"
else
    echo -e "${RED}✗ Simple storage tests failed${NC}"
    echo "Continuing anyway..."
fi
echo ""

# Step 10: Run Integration Tests
echo -e "${YELLOW}[Step 10/10] Running integration tests...${NC}"
if python test_storage_integration.py; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
else
    echo -e "${RED}✗ Integration tests failed${NC}"
    echo "See logs above for details"
fi
echo ""

# Summary
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Services running:"
docker-compose ps
echo ""
echo "Next steps:"
echo "1. View logs: docker-compose logs -f"
echo "2. Access MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "3. Test manually: See QUICKSTART.md"
echo ""
echo "To stop services: docker-compose down"
echo ""

