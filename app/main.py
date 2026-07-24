from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.brands import router
from app.services.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="Yarnit AI Visibility Platform",
    description="Track brand visibility across AI engines",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(router)

@app.on_event("startup")
async def on_startup():
    start_scheduler()

@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()

@app.get("/")
async def root():
    return {"message": "Yarnit AI Visibility Platform is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}