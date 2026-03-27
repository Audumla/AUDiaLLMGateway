#!/bin/bash
# Monitoring API testing script
# Validates monitoring data provider code structure, tests, and containerization

set -e

DASHBOARD_ROOT="src/monitoring"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}Monitoring Data Provider Test Suite${NC}"
echo -e "${YELLOW}=====================================${NC}"
echo

# 1. Check Python syntax
echo -e "${YELLOW}[1/5] Checking Python syntax...${NC}"
python_files=$(find "$DASHBOARD_ROOT" -name "*.py" -type f)
for file in $python_files; do
    python -m py_compile "$file" || { echo -e "${RED}Syntax error in $file${NC}"; exit 1; }
done
echo -e "${GREEN}✓ All Python files valid${NC}"
echo

# 2. Check module structure
echo -e "${YELLOW}[2/5] Verifying module structure...${NC}"
required_modules=(
    "__init__.py"
    "main.py"
    "manifest_loader.py"
    "docker_handler.py"
    "action_runner.py"
    "models/__init__.py"
    "models/manifest.py"
    "models/prometheus.py"
    "models/api.py"
    "models/errors.py"
    "routers/__init__.py"
    "routers/manifests.py"
    "services/__init__.py"
    "tests/__init__.py"
)

missing=0
for module in "${required_modules[@]}"; do
    if [ ! -f "$DASHBOARD_ROOT/$module" ]; then
        echo -e "${RED}✗ Missing: $module${NC}"
        missing=$((missing + 1))
    fi
done

if [ $missing -eq 0 ]; then
    echo -e "${GREEN}✓ All required modules present${NC}"
else
    echo -e "${RED}✗ $missing modules missing${NC}"
    exit 1
fi
echo

# 3. Run pytest
echo -e "${YELLOW}[3/5] Running pytest suite...${NC}"
cd "$PROJECT_ROOT"
python -m pytest "$DASHBOARD_ROOT/tests/" -v --tb=short 2>&1 | tail -20
test_result=${PIPESTATUS[0]}

if [ $test_result -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
echo

# 4. Check Docker build configuration
echo -e "${YELLOW}[4/5] Verifying Docker configuration...${NC}"
if [ ! -f "$DASHBOARD_ROOT/Dockerfile" ]; then
    echo -e "${RED}✗ Dockerfile not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dockerfile present${NC}"

if [ ! -f "docker-compose.dashboard.yml" ]; then
    echo -e "${YELLOW}⚠ docker-compose.dashboard.yml not found${NC}"
else
    echo -e "${GREEN}✓ docker-compose.dashboard.yml present${NC}"
fi
echo

# 5. Summary
echo -e "${YELLOW}[5/5] Test Summary${NC}"
test_count=$(python -m pytest "$DASHBOARD_ROOT/tests/" --collect-only -q | tail -1)
echo "Total tests: $test_count"

echo
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}All monitoring API tests passed!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo

# 6. Next steps
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Build and run Docker image:"
echo "   docker build -f src/monitoring/Dockerfile -t audia-monitoring:phase-1 ."
echo "   docker run -p 8080:8080 audia-monitoring:phase-1"
echo
echo "2. Or use docker-compose:"
echo "   docker-compose -f docker-compose.dashboard.yml up -d dashboard"
echo
echo "3. Test the API:"
echo "   curl http://localhost:8080/healthz"
echo "   curl http://localhost:8080/api/v1/manifests"
echo
