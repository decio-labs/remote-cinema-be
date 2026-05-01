# handles project initialization 

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import routers

app = FastAPI(
    debug=False, title="Remote Cinema",
    version="1.0.0", docs_url="/swagger-ui-docs",
    redoc_url="/swagger-ui-redocs"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=['*']
)

app.include_router(routers.api_router)

