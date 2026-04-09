import os
from dotenv import load_dotenv

load_dotenv()

# Primary database URL used by the application and Alembic.
# Prefer setting DATABASE_URL in a local .env file or the environment.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
