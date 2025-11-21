"""
FastAPI Application
Main entry point for the API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from agent_platform.db.database import init_db
from agent_platform.api.routes import (
    email_agent,
    tasks,
    decisions,
    questions,
    dashboard,
    review_queue,
    attachments,
    threads,
    history_scan,
    webhooks,
    auth,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    print("🚀 Initializing database...")
    init_db()
    print("✅ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title="Agent Platform API",
    description="REST API for Digital Twin Email Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration (for Next.js Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",  # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "agent-platform-api"}


# Include Routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(email_agent.router, prefix="/api/v1", tags=["email-agent"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(decisions.router, prefix="/api/v1", tags=["decisions"])
app.include_router(questions.router, prefix="/api/v1", tags=["questions"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(review_queue.router, prefix="/api/v1", tags=["review-queue"])
app.include_router(attachments.router)  # Already has /api/v1 prefix
app.include_router(threads.router)  # Already has /api/v1 prefix
app.include_router(history_scan.router)  # Already has /api/v1 prefix
app.include_router(webhooks.router)  # Already has /api/v1 prefix


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
