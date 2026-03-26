import os
import asyncio
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
import uvicorn

# 导入异步网络客户端及各家搜索引擎模块
from PicImageSearch import (
    Network, AnimeTrace, Ascii2D,BaiDu, Bing, Copyseeker,
    EHentai, GoogleLens, Iqdb, SauceNAO, Tineye, TraceMoe, Yandex
)

app = FastAPI(title="PicImageSearch 聚合搜图服务端", description="一次调用返回全网各大引擎的最佳搜图结果")

import yaml

with open('./config.yaml', 'r', encoding='utf-8') as f:
   result = yaml.load(f.read(), Loader=yaml.FullLoader)
proxy=result["proxy"]
SAUCENAO_API_KEY =result["SAUCENAO_API_KEY"]
port=result["port"]
if proxy:
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

@app.post("/search")
async def search_image(file: UploadFile = File(...)):
    """接收上传的图片，并发调用全网引擎并返回各个引擎的最佳识别结果"""

    # 1. 暂存上传图片到本地临时文件（PicImageSearch 接口通常需要传递本地路径或 URL）
    try:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存上传图片失败: {e}")
    print(f"接收到搜图请求，图片已缓存：{tmp_path}")
    try:
        # 2. 建立统一的异步网络客户端
        async with Network() as client:
            # 初始化所有支持的引擎实例
            engines = {
                "AnimeTrace": AnimeTrace(client=client),
                "Ascii2D": Ascii2D(client=client),
                "BaidDu": BaiDu(client=client),
                "Bing": Bing(client=client),
                "Copyseeker": Copyseeker(client=client),
                "EHentai": EHentai(client=client),
                "GoogleLens": GoogleLens(client=client),
                "Iqdb": Iqdb(client=client),
                "SauceNAO": SauceNAO(client=client, api_key=SAUCENAO_API_KEY) if SAUCENAO_API_KEY else SauceNAO(
                    client=client),
                "Tineye": Tineye(client=client),
                "TraceMoe": TraceMoe(client=client),
                "Yandex": Yandex(client=client),
            }

            # 内部异步执行封装：查询并提取最佳结果 (raw[0])
            async def fetch_best_result(engine_name, engine_instance):
                try:
                    # 使用临时文件路径进行搜图
                    resp = await engine_instance.search(file=tmp_path)

                    # 检查是否有返回值且 raw 数据不为空
                    if resp and hasattr(resp, 'raw') and len(resp.raw) > 0:
                        best = resp.raw[0]  # 取最大可能结果(Top 1)

                        return {
                            "engine": engine_name,
                            "status": "success",
                            # 动态提取属性，兼容不同引擎的数据结构差异
                            "title": getattr(best, "title", getattr(best, "origin", "未知标题")),
                            "author": getattr(best, "author", None),
                            "url": getattr(best, "url", getattr(best, "source", None)),
                            "thumbnail": getattr(best, "thumbnail", getattr(best, "pic", None)),
                            "similarity": getattr(best, "similarity", getattr(best, "detail", "未知相似度"))
                        }
                    return {"engine": engine_name, "status": "not_found", "message": "未找到匹配结果"}
                except Exception as e:
                    return {"engine": engine_name, "status": "error", "message": str(e)}

            # 3. 使用 asyncio.gather 并发启动所有引擎的搜索任务
            tasks = [fetch_best_result(name, eng) for name, eng in engines.items()]
            results = await asyncio.gather(*tasks)

        # 构建最终统一的 JSON 返回体
        return {"status": "success", "results": results}

    finally:
        # 4. 清理暂存的图片文件，防止磁盘堵塞
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    # 启动命令
    print("🚀 聚合搜图引擎已启动，正在监听 8000 端口...")
    uvicorn.run(app, host="0.0.0.0", port=port)