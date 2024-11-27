import aiohttp
import json


async def fetch_prompt():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/story/generate') as response:
            if response.status == 200:
                story =  await response.text()  
                LK_prompt = json.loads(story)
                return LK_prompt
            else:
                return "Default prompt text"  


