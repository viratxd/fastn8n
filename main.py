from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from utils.gitdl import download_github_zip
from utils.unzip import extract_zip, adjust_extracted_folder
from utils.routeset import setup_dynamic_route
from utils.jsonmem import load_plugins_memory, save_plugins_memory
import os
import shutil
from config import PLUGINS_DIR
import uvicorn

app = FastAPI()

if not os.path.exists(PLUGINS_DIR):
    os.makedirs(PLUGINS_DIR)

class PluginRequest(BaseModel):
    route_name: str
    github_repo_url: str

class UninstallRequest(BaseModel):
    repo_name: str

@app.post("/install_plugin")
async def install_plugin(plugin: PluginRequest):
    route_name = plugin.route_name.strip("/")
    repo_url = plugin.github_repo_url
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    plugin_path = os.path.join(PLUGINS_DIR, repo_name)
    zip_path = f"{plugin_path}.zip"

    plugins_memory = load_plugins_memory()

    if repo_name in plugins_memory:
        return {"message": f"Plugin '{repo_name}' already installed at /{plugins_memory[repo_name]['route']}"}

    try:
        await download_github_zip(repo_url, zip_path)
        await extract_zip(zip_path, PLUGINS_DIR)
        plugin_path = await adjust_extracted_folder(repo_name, PLUGINS_DIR)
        await setup_dynamic_route(app, route_name, plugin_path, repo_name)

        plugins_memory[repo_name] = {
            "route": route_name,
            "github_url": repo_url,
            "installed_at": str(os.path.getmtime(plugin_path)),
            "status": "installed"
        }
        save_plugins_memory(plugins_memory)

        return {"message": f"Plugin '{repo_name}' installed at /{route_name}"}

    except Exception as e:
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/uninstall_plugin")
async def uninstall_plugin(request: UninstallRequest):
    repo_name = request.repo_name
    plugin_path = os.path.join(PLUGINS_DIR, repo_name)
    plugins_memory = load_plugins_memory()

    if repo_name not in plugins_memory:
        raise HTTPException(status_code=404, detail=f"Plugin '{repo_name}' not found")

    try:
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
        del plugins_memory[repo_name]
        save_plugins_memory(plugins_memory)
        return {"message": f"Plugin '{repo_name}' uninstalled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/plugins")
async def list_plugins():
    return load_plugins_memory()

@app.get("/plugin_status/{repo_name}")
async def plugin_status(repo_name: str):
    plugins_memory = load_plugins_memory()
    if repo_name not in plugins_memory:
        raise HTTPException(status_code=404, detail=f"Plugin '{repo_name}' not found")
    return plugins_memory[repo_name]

@app.get("/")
async def root():
    return {"message": "FastAPI Plugin Loader"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)