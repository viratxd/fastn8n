import aiohttp
from fastapi import HTTPException

async def download_github_zip(repo_url: str, zip_path: str):
    """Asynchronously download GitHub repo as ZIP file."""
    zip_url = f"{repo_url}/archive/refs/heads/main.zip"
    async with aiohttp.ClientSession() as session:
        async with session.get(zip_url) as response:
            if response.status != 200:
                raise HTTPException(status_code=400, detail="Invalid GitHub URL or repo not accessible")
            with open(zip_path, "wb") as f:
                f.write(await response.read())