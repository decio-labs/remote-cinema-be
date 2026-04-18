from fastapi.responses import JSONResponse

import src.manage

app = src.manage.app

@app.get("/read_root")
def read_root():
    return JSONResponse(content={"status": True, 'details': "Backend is running"}, status_code=200)
