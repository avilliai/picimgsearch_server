搜图服务端。    
可以去release下载打包版。    

代码示例，你想写同步的也行。    
```python
import traceback

import asyncio
import httpx

img="img.jpg"
async def search_(img:str):
    async with httpx.AsyncClient() as client:
        try:
            files = {
                "file": (img, open(img, "rb"), "image/jpeg")
            }

            headers = {
                "accept": "application/json"
            }
            response = await client.post("http://127.0.0.1:5008/search",headers=headers,files=files,timeout=None)
        except Exception as e:
            traceback.print_exc()
            print(e)
        print(response.json())

asyncio.run(search_(img))
```
