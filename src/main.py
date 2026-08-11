from fastapi import FastAPI
from src.api.knowledge import router as knowledge_router
from src.api.upload import router as upload_router

from contextlib import asynccontextmanager
from src.job_runner import job_runner

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the bounded in-process job runner
    await job_runner.start()
    yield
    # Shutdown: Stop the job runner gracefully
    await job_runner.stop()

app = FastAPI(
    title="SecureOps Local",
    description=(
        "Local incident-review decision-support prototype "
        "for Linux SSH authentication logs."
    ),
    version="0.1.0",
    docs_url="/docs",  # Swagger UI enabled by default here
    redoc_url=None,    # Disable redoc as per requirements for Swagger UI only
    lifespan=lifespan,
)

app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(knowledge_router, prefix="/api", tags=["knowledge"])

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
