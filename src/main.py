from fastapi import FastAPI

app = FastAPI(
    title="SecureOps Local",
    description=(
        "Local incident-review decision-support prototype "
        "for Linux SSH authentication logs."
    ),
    version="0.1.0",
    docs_url="/docs",  # Swagger UI enabled by default here
    redoc_url=None,    # Disable redoc as per requirements for Swagger UI only
)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
