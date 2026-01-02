#!/bin/bash
set -e

echo "=========================================="
echo "  TensorWall Demo - Starting..."
echo "=========================================="

cd /app

# Initialize SQLite database if not exists
if [ ! -f /app/data/tensorwall.db ]; then
    echo "[1/3] Initializing database..."

    python3 << 'INIT_DB'
import asyncio
from backend.db.session import engine
from backend.db.models import Base

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  -> Tables created")

asyncio.run(init())
INIT_DB

    echo "[2/3] Seeding demo data..."

    python3 << 'SEED_DATA'
import asyncio
import secrets
import random
from datetime import datetime, timedelta

async def seed():
    from passlib.context import CryptContext
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import (
        Application, ApiKey, Budget, PolicyRule, Feature, UsageRecord,
        Organization, User, UserRole, Environment, BudgetPeriod,
        PolicyAction, TenantStatus, TenantTier, SetupState
    )
    from backend.core.auth import hash_api_key

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with AsyncSessionLocal() as session:
        # Setup state
        session.add(SetupState(key="setup_completed", value="true"))

        # Organization
        org = Organization(
            org_id="org_demo",
            name="Demo Organization",
            slug="demo-org",
            status=TenantStatus.ACTIVE,
            tier=TenantTier.PROFESSIONAL,
            owner_email="demo@tensorwall.ai",
            created_at=datetime.utcnow(),
        )
        session.add(org)
        await session.flush()

        # Admin user
        admin = User(
            email="demo@tensorwall.ai",
            hashed_password=pwd_context.hash("demo123"),
            full_name="Demo Admin",
            role=UserRole.ADMIN,
            org_id=org.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(admin)

        # Applications with realistic names
        apps_config = [
            ("chatbot-prod", "Production Chatbot", "Customer support chatbot"),
            ("internal-copilot", "Internal Copilot", "Employee productivity assistant"),
            ("data-analyst", "Data Analyst AI", "Business intelligence queries"),
        ]

        apps = []
        for app_id, name, desc in apps_config:
            app = Application(
                app_id=app_id,
                name=name,
                owner="demo@tensorwall.ai",
                description=desc,
                is_active=True,
                allowed_providers=["openai", "anthropic", "mock"],
                allowed_models=["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022", "mock-gpt-4"],
                created_at=datetime.utcnow(),
            )
            session.add(app)
            apps.append(app)

        await session.flush()

        # API Keys
        for app in apps:
            key_raw = f"gw_demo_{secrets.token_urlsafe(16)}"
            api_key = ApiKey(
                key_hash=hash_api_key(key_raw),
                key_prefix=key_raw[:12],
                name=f"{app.name} Key",
                application_id=app.id,
                environment=Environment.PRODUCTION,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(api_key)

        # Budgets (different limits per app)
        budget_config = [(apps[0].id, 500, 750), (apps[1].id, 200, 300), (apps[2].id, 100, 150)]
        for app_id, soft, hard in budget_config:
            budget = Budget(
                application_id=app_id,
                soft_limit_usd=float(soft),
                hard_limit_usd=float(hard),
                period=BudgetPeriod.MONTHLY,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            session.add(budget)

        # Security Policies
        policies_config = [
            ("Block PII Exposure", apps[0].id, {"blocked_patterns": ["ssn", "credit_card", "password"]}, PolicyAction.DENY, 10),
            ("Restrict to GPT-4o-mini", apps[1].id, {"allowed_models": ["gpt-4o-mini", "mock-gpt-4"]}, PolicyAction.ALLOW, 50),
            ("Max 2000 tokens", apps[2].id, {"max_tokens": 2000}, PolicyAction.ALLOW, 30),
        ]
        for name, app_id, conditions, action, priority in policies_config:
            policy = PolicyRule(
                name=name,
                description=f"Security policy: {name}",
                application_id=app_id,
                conditions=conditions,
                action=action,
                priority=priority,
                is_enabled=True,
                created_at=datetime.utcnow(),
            )
            session.add(policy)

        # Generate 30 days of usage data
        providers = ["openai", "anthropic"]
        models_list = ["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet-20241022"]

        for app in apps:
            base_requests = 100 if "chatbot" in app.app_id else 40
            for day_offset in range(30):
                date = datetime.utcnow() - timedelta(days=day_offset)
                daily_count = random.randint(base_requests - 20, base_requests + 20)

                for _ in range(daily_count):
                    provider = random.choice(providers)
                    model = random.choice(models_list)
                    input_tokens = random.randint(100, 2000)
                    output_tokens = random.randint(50, 1000)

                    # Realistic cost calculation
                    if "gpt-4o-mini" in model:
                        cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
                    elif "gpt-4o" in model:
                        cost = (input_tokens * 0.005 + output_tokens * 0.015) / 1000
                    else:  # Claude
                        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000

                    usage = UsageRecord(
                        request_id=f"req_{secrets.token_hex(8)}",
                        app_id=app.app_id,
                        feature="default",
                        environment=Environment.PRODUCTION,
                        provider=provider,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=cost,
                        latency_ms=random.randint(100, 2000),
                        created_at=date,
                    )
                    session.add(usage)

        await session.commit()
        print("  -> Demo data seeded")

asyncio.run(seed())
SEED_DATA

else
    echo "[1/3] Database exists, skipping init"
    echo "[2/3] Skipping seed"
fi

echo "[3/3] Starting services..."

# Start backend
echo "  -> Starting backend on :8000"
cd /app
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 &
BACKEND_PID=$!

# Wait for backend
echo "  -> Waiting for backend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
        echo "  -> Backend ready"
        break
    fi
    sleep 1
done

# Start frontend
echo "  -> Starting frontend on :3000"
cd /app/frontend
BACKEND_URL=http://localhost:8000 npm run start -- -p 3000 &
FRONTEND_PID=$!

# Wait for frontend
echo "  -> Waiting for frontend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo "  -> Frontend ready"
        break
    fi
    sleep 1
done

# Start Caddy reverse proxy
echo "  -> Starting Caddy on :7860"
caddy run --config /etc/caddy/Caddyfile &
CADDY_PID=$!

echo ""
echo "=========================================="
echo "  TensorWall Demo Ready!"
echo "=========================================="
echo ""
echo "  URL: http://localhost:7860"
echo "  Login: demo@tensorwall.ai / demo123"
echo ""
echo "  This is a demo with mock LLM providers."
echo "  For production, deploy locally."
echo ""
echo "=========================================="

# Keep running
wait $CADDY_PID $BACKEND_PID $FRONTEND_PID
