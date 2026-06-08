#!/bin/bash
# =============================================================================
# SilverTrade AI — LetsEncrypt SSL Initialization
# =============================================================================
# Run this script once on the production server to obtain SSL certificates.
# It starts nginx in HTTP-only mode, requests certificates via Certbot,
# and then reloads nginx with the new SSL config.
#
# Usage:
#   export DOMAIN=your-domain.com
#   export EMAIL=admin@your-domain.com
#   bash deploy/init-letsencrypt.sh
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-admin@${DOMAIN}}"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: DOMAIN not set.${NC}"
    echo "Usage: DOMAIN=your-domain.com EMAIL=admin@your-domain.com bash deploy/init-letsencrypt.sh"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SilverTrade AI — SSL Initialization${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# ── Step 1: Ensure docker compose is available ──────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is not installed.${NC}"
    exit 1
fi

# ── Step 2: Create required directories ─────────────────────────────────────
echo -e "${YELLOW}[1/5] Creating required directories...${NC}"
mkdir -p nginx/conf.d certbot/www certbot/conf

# ── Step 3: Start nginx in HTTP-only mode for domain validation ────────────
echo -e "${YELLOW}[2/5] Starting nginx in HTTP-only mode for domain validation...${NC}"

# Create a temporary nginx config that only handles HTTP + certbot challenges
cat > nginx/conf.d/le-http-only.conf << 'LEHTTP'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 "ACME challenge server is running";
    }
}
LEHTTP

# Start nginx container only (with certbot challenge handling)
docker compose -f "$COMPOSE_FILE" up -d nginx --no-deps
echo "Waiting for nginx to start..."
sleep 3

# ── Step 4: Obtain SSL certificates via Certbot ─────────────────────────────
echo -e "${YELLOW}[3/5] Requesting SSL certificates from LetsEncrypt...${NC}"

docker run --rm \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    certbot/certbot \
    certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --domain "$DOMAIN" \
    --non-interactive

echo -e "${GREEN}✓ SSL certificates obtained!${NC}"

# ── Step 5: Clean up temporary config and restart full stack ────────────────
echo -e "${YELLOW}[4/5] Cleaning up temporary config...${NC}"
rm -f nginx/conf.d/le-http-only.conf

echo -e "${YELLOW}[5/5] Restarting full stack with SSL...${NC}"
docker compose -f "$COMPOSE_FILE" down
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  SSL setup complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Your SilverTrade AI instance is now running at:"
echo "  https://$DOMAIN"
echo ""
echo "Certificates will auto-renew every 12 hours."
echo "Manual renewal: docker compose -f $COMPOSE_FILE run --rm certbot renew"
echo ""
