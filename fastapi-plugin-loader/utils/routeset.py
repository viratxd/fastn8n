import importlib.util
import sys
import os
import asyncio
import subprocess
from pathlib import Path
from fastapi import HTTPException, FastAPI, Request, Query
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
    """Install requirements.txt into shared virtual environment synchronously for reliability."""
    requirements_file = Path(plugin_path) / "requirements.txt"
    if requirements_file.exists():
        await ensure_shared_venv()
        pip_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "pip"
        
        # Debugging: Print paths and check existence
        print(f"pip_path: {pip_path}, exists: {pip_path.exists()}")
        print(f"requirements_file: {requirements_file}, exists: {requirements_file.exists()}")

        # Synchronous call for reliability
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
    """Set up dynamic route from plugin's main.py for GET and POST."""
    main_file = Path(plugin_path) / "main.py"
    if not main_file.exists():
        raise HTTPException(status_code=400, detail="No 'main.py' found in repo")

    await install_requirements(plugin_path)

    python_path = SHARED_VENV_PATH / ("bin" if os.name != "nt" else "Scripts") / "python"
    if not python_path.exists():
        python_path = sys.executable  # Fallback to system Python

    spec = importlib.util.spec_from_file_location(repo_name, str(main_file))
    module = importlib.util.module_from_spec(spec)
    sys.modules[repo_name] = module
    spec.loader.exec_module(module)

    if not hasattr(module, "handler"):
        raise HTTPException(status_code=400, detail="No 'handler' function in main.py")

    @app.get(f"/{route_name}")
    async def get_route(query: str = Query(None)):
        data = {"query": query} if query else {}
        return module.handler(method="GET", data=data)

    @app.post(f"/{route_name}")
    async def post_route(request: Request):
        data = await request.json()
        return module.handler(method="POST", data=data)