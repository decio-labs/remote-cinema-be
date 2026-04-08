"""
    Handles Loading of apps and declearative base
    Intializing fastapi
"""
from .config.base import Base


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    debug=True, title="Remote Cinema",
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

