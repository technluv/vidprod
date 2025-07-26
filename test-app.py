from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "VidProd API is running!"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "vidprod"}

@app.get("/ui", response_class=HTMLResponse)
async def ui():
    return """
    <html>
        <head>
            <title>VidProd Test</title>
        </head>
        <body>
            <h1>VidProd Upload Test</h1>
            <p>This is a test page to verify port visibility in Codespaces.</p>
            <p>Current time: <span id="time"></span></p>
            <script>
                document.getElementById('time').textContent = new Date().toLocaleString();
            </script>
        </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)