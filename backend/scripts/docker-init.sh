#!/bin/bash
set -e

echo "=== TensorWall Initialization ==="
echo ""

# Wait for database
echo "Waiting for database..."
python -c "
import asyncio
import sys
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

async def wait_db():
    for i in range(30):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text('SELECT 1'))
            return True
        except Exception:
            print(f'  Attempt {i+1}/30...')
            await asyncio.sleep(1)
    return False

if not asyncio.run(wait_db()):
    print('ERROR: Database not available')
    sys.exit(1)
print('Database ready.')
"

# Check if already initialized
echo ""
echo "Checking setup state..."
SETUP_DONE=$(python -c "
import asyncio
from sqlalchemy import text
from backend.db.session import AsyncSessionLocal

async def check():
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(\"SELECT value FROM setup_state WHERE key = 'setup_completed'\")
            )
            row = result.fetchone()
            return 'true' if row and row[0] == 'true' else 'false'
    except Exception:
        return 'false'

print(asyncio.run(check()))
" 2>/dev/null || echo "false")

if [ "$SETUP_DONE" = "true" ]; then
    echo "Setup already completed. Skipping initialization."
    exit 0
fi

# Run setup wizard in non-interactive mode
echo ""
echo "Running setup wizard..."

# Generate password if not provided
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))")
    echo ""
    echo "=================================================="
    echo "  GENERATED ADMIN PASSWORD (SAVE THIS!)"
    echo "  $ADMIN_PASSWORD"
    echo "=================================================="
    echo ""
fi

# Run the setup
python -m backend.cli setup wizard \
    --non-interactive \
    --admin-email "${ADMIN_EMAIL:-admin@example.com}" \
    --admin-password "$ADMIN_PASSWORD" \
    --seed "${SEED_DATA:-development}"

echo ""
echo "=== Initialization Complete ==="
