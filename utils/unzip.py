import zipfile
import os
import shutil
import asyncio

async def extract_zip(zip_path: str, extract_to: str):
    """Asynchronously extract ZIP file to specified directory and remove ZIP."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: (
        zipfile.ZipFile(zip_path, "r").extractall(extract_to),
        os.remove(zip_path)
    ))

async def adjust_extracted_folder(repo_name: str, plugins_dir: str):
    """Rename extracted folder from GitHub ZIP format."""
    extracted_folder = os.path.join(plugins_dir, f"{repo_name}-main")
    plugin_path = os.path.join(plugins_dir, repo_name)
    if os.path.exists(extracted_folder):
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
        os.rename(extracted_folder, plugin_path)
    return plugin_path