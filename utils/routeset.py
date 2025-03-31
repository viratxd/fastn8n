import importlib.util
import sys
import os
import asyncio
import subprocess
from pathlib import Path
from fastapi import HTTPException, FastAPI, Request, Query
from fastapi.responses import FileResponse
from config import SHARED_VENV_DIR

SHARED_VENV_PATH = Path(SHARED_VENV_DIR).resolve()

async def ensure_shared_venv():
    """Ensure shared virtual environment exists and has pip installed."""
    if not SHARED_VENV_PATH.exists():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "venv", str(SHARED_VENV_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to create virtual environment: {stderr.decode()}")

    pip_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "pip"
    if not pip_path.exists():
        python_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "python"
        if not python_path.exists():
            raise HTTPException(status_code=500, detail=f"Python not found in virtual environment at {python_path}")

        process = await asyncio.create_subprocess_exec(
            str(python_path), "-m", "ensurepip",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to ensure pip: {stderr.decode()}")

        process = await asyncio.create_subprocess_exec(
            str(python_path), "-m", "pip", "install", "--upgrade", "pip",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Failed to upgrade pip: {stderr.decode()}")

        if not pip_path.exists():
            raise HTTPException(status_code=500, detail=f"pip still not found after setup at {pip_path}")

async def install_requirements(plugin_path: str):
    """Install requirements.txt into shared virtual environment synchronously."""
    requirements_file = Path(plugin_path) / "requirements.txt"
    if requirements_file.exists():
        await ensure_shared_venv()
        pip_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "pip"
        
        print(f"pip_path: {pip_path}, exists: {pip_path.exists()}")
        print(f"requirements_file: {requirements_file}, exists: {requirements_file.exists()}")

        try:
            result = subprocess.run(
                [str(pip_path), "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Requirements installed successfully: {result.stdout}")
        except subprocess.CalledProcessError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install requirements: {e.stderr}\nCommand output: {e.stdout}"
            )

async def setup_dynamic_route(app: FastAPI, route_name: str, plugin_path: str, repo_name: str):
    """Set up dynamic route from plugin's main.py for GET and POST with async support."""
    main_file = Path(plugin_path) / "main.py"
    if not main_file.exists():
        raise HTTPException(status_code=400, detail="No 'main.py' found in repo")

    await install_requirements(plugin_path)

    python_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "python"
    if not python_path.exists():
        python_path = sys.executable

    spec = importlib.util.spec_from_file_location(repo_name, str(main_file))
    module = importlib.util.module_from_spec(spec)
    sys.modules[repo_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "handler"):
        raise HTTPException(status_code=400, detail="No 'handler' function in main.py")

    is_async_handler = asyncio.iscoroutinefunction(module.handler)

    @app.get(f"/{route_name}")
    async def get_route(query: str = Query(None)):
        data = {"text": query} if query else {}
        if is_async_handler:
            response = await module.handler(method="GET", data=data)
        else:
            response = module.handler(method="GET", data=data)
        if isinstance(response, FileResponse):
            return response
        return response

    @app.post(f"/{route_name}")
    async def post_route(request: Request):
        data = await request.json()
        if is_async_handler:
            response = await module.handler(method="POST", data=data)
        else:
            response = module.handler(method="POST", data=data)
        if isinstance(response, FileResponse):
            return response
        return response
