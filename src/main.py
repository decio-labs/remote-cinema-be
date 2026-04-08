from fastapi.responses import JSONResponse

from .manage import app

@app.get("/read_root")
def read_root():
    return JSONResponse(content={"status": True, 'details': "Backend is running"}, status_code=200)
