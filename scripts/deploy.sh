#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# FinPilot AI — Single-VM Deployment Script
# Target: Ubuntu 22.04+ / Oracle Linux 8+ (ARM or x86)
# ─────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[deploy]${NC} $1"; }
ok()   { echo -e "${GREEN}[  ok]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
fail() { echo -e "${RED}[fail]${NC} $1"; exit 1; }

# ── Check prerequisites ──
for cmd in curl git; do
    command -v $cmd &>/dev/null || fail "$cmd is required. Install it first."
done

# ── Collect variables ──
DOMAIN="${DOMAIN:-}"
DB_PASSWORD="${DB_PASSWORD:-}"
APP_JWT_SECRET="${APP_JWT_SECRET:-}"

if [ -z "$DOMAIN" ]; then
    PUBLIC_IP=$(curl -4 -s ifconfig.me 2>/dev/null || curl -4 -s icanhazip.com 2>/dev/null || echo "")
    if [ -n "$PUBLIC_IP" ]; then
        DOMAIN="http://$PUBLIC_IP"
        warn "No DOMAIN set. Using public IP: $DOMAIN (HTTP only)"
    else
        DOMAIN="http://localhost"
        warn "Could not detect public IP. Using: $DOMAIN"
    fi
fi

if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(openssl rand -base64 24 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || echo "change_me_in_production_32_chars_min!!")
    ok "Generated DB_PASSWORD"
fi

if [ -z "$APP_JWT_SECRET" ]; then
    APP_JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-this-secret-in-production-minimum-32-chars!!")
    ok "Generated APP_JWT_SECRET"
fi

# ── Install Docker if missing ──
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker "$USER"
    ok "Docker installed. You may need to re-login for group changes."
fi

if ! docker compose version &>/dev/null; then
    log "Installing Docker Compose plugin..."
    sudo apt-get update -qq && sudo apt-get install -y -qq docker-compose-plugin 2>/dev/null || \
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}; mkdir -p "$DOCKER_CONFIG/cli-plugins" && \
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o "$DOCKER_CONFIG/cli-plugins/docker-compose" && \
    chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
    ok "Docker Compose installed"
fi

ok "Docker is ready"

# ── Clone or pull repo ──
REPO_DIR="${REPO_DIR:-$HOME/finpilot-ai}"
if [ -d "$REPO_DIR" ]; then
    log "Updating existing repo at $REPO_DIR..."
    cd "$REPO_DIR"
    git pull
else
    log "Cloning repo..."
    git clone https://github.com/YOUR_ORG/finpilot-ai.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# ── Create .env ──
log "Creating .env..."
cat > .env <<EOF
# ── Database ──
SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/fhss
SPRING_DATASOURCE_USERNAME=fhss
SPRING_DATASOURCE_PASSWORD=$DB_PASSWORD

# ── Spring Profile ──
SPRING_PROFILES_ACTIVE=docker

# ── ML Service ──
ML_SERVICE_URL=http://ml-service:8000

# ── Redis ──
REDIS_HOST=redis
REDIS_PORT=6379

# ── JWT ──
APP_JWT_SECRET=$APP_JWT_SECRET

# ── CORS ──
CORS_ALLOWED_ORIGINS=$DOMAIN

# ── Domain (used by Caddy for SSL + CORS) ──
DOMAIN=$DOMAIN
CORS_ORIGIN=$DOMAIN

# ── PostgreSQL password (referenced by compose) ──
DB_PASSWORD=$DB_PASSWORD
EOF
ok ".env created"

# ── Build and start ──
log "Building and starting all services (first build may take 5-10 minutes)..."
cd "$REPO_DIR"
docker compose -f docker/docker-compose.deploy.yml build
docker compose -f docker/docker-compose.deploy.yml up -d

# ── Wait for healthy ──
log "Waiting for services to become healthy..."
sleep 10

for i in $(seq 1 30); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/actuator/health 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        ok "Backend is healthy"
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Backend health check timed out. Check logs: docker compose -f docker/docker-compose.deploy.yml logs backend"
    fi
    sleep 5
done

# ── Seed database ──
log "Seeding database with demo profiles..."
cd "$REPO_DIR/synthetic-data"
pip install -q psycopg2-binary 2>/dev/null || true
python seed.py 2>/dev/null && ok "Database seeded" || warn "Seeding failed (run manually: cd synthetic-data && python seed.py)"

# ── Test ──
log "Testing scoring endpoint..."
SCORE=$(curl -s -X POST http://localhost/api/v1/score/CUST00042 2>/dev/null || echo "")
if echo "$SCORE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('composite_score',''))" 2>/dev/null; then
    ok "Scoring API works!"
else
    warn "Scoring test returned unexpected response. Check logs."
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  FinPilot AI is deployed!${NC}"
echo -e "${GREEN}  URL: ${CYAN}$DOMAIN${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
echo "  Demo customer IDs: CUST00042, CUST00011, CUST00087, CUST00134"
echo ""
echo "  Commands:"
echo "    Logs:    docker compose -f docker/docker-compose.deploy.yml logs -f"
echo "    Restart: docker compose -f docker/docker-compose.deploy.yml restart"
echo "    Stop:    docker compose -f docker/docker-compose.deploy.yml down"
echo "    Update:  git pull && docker compose -f docker/docker-compose.deploy.yml up -d --build"
echo ""
