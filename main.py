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
import asyncio

app = FastAPI()

if not os.path.exists(PLUGINS_DIR):
    os.makedirs(PLUGINS_DIR)

class PluginRequest(BaseModel):
    route_name: str
    github_repo_url: str

class UninstallRequest(BaseModel):
    repo_name: str

async def install_plugin_logic(plugin: PluginRequest):
    route_name = plugin.route_name.strip("/")
    repo_url = plugin.github_repo_url
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    plugin_path = os.path.join(PLUGINS_DIR, repo_name)
    zip_path = f"{plugin_path}.zip"

    plugins_memory = load_plugins_memory()

    # Agar plugin pehle se installed hai, to sirf route setup karo
    if repo_name in plugins_memory and os.path.exists(plugin_path):
        print(f"Plugin '{repo_name}' already exists, setting up route only.")
        await setup_dynamic_route(app, route_name, plugin_path, repo_name)
        return {"message": f"Plugin '{repo_name}' route re-established at /{route_name}"}

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

@app.post("/install_plugin")
async def install_plugin(plugin: PluginRequest):
    return await install_plugin_logic(plugin)

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

# Startup event to reload routes for existing plugins
@app.on_event("startup")
async def startup_event():
    plugins_memory = load_plugins_memory()
    for repo_name, plugin_data in plugins_memory.items():
        if plugin_data.get("status") == "installed":
            plugin_path = os.path.join(PLUGINS_DIR, repo_name)
            if os.path.exists(plugin_path):
                print(f"Reloading route for existing plugin: {repo_name}")
                await setup_dynamic_route(app, plugin_data["route"], plugin_path, repo_name)
            else:
                print(f"Re-installing plugin: {repo_name}")
                plugin_request = PluginRequest(
                    route_name=plugin_data["route"],
                    github_repo_url=plugin_data["github_url"]
                )
                await install_plugin_logic(plugin_request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
