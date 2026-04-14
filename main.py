import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import io
import argparse
import asyncio

app = FastAPI(title="Edge TTS API")

# 启用 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    input: Optional[str] = None
    voice: Optional[str] = "zh-CN-XiaoxiaoNeural"
    model: Optional[str] = None
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

async def get_tts_stream(text: str, voice: str, rate: str, pitch: str):
    try:
        print(f"Generating TTS: voice={voice}, rate={rate}, pitch={pitch}, text_len={len(text)}")
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except Exception as e:
        print(f"TTS Stream Error: {e}")
        # 这里不抛出异常，因为已经在生成流中，但我们需要确保客户端知道出错了
        # 通常这种中途失败会导致音频截断或不可用
        raise e

@app.get("/v1/models")
@app.get("/voices")
async def list_voices():
    voices = await edge_tts.VoicesManager.create()
    voice_list = voices.voices
    # 格式化以适配 OpenAI 结构或自定义结构
    return {
        "data": [{"id": v["ShortName"], "name": v["FriendlyName"]} for v in voice_list],
        "voices": {v["ShortName"]: v["FriendlyName"] for v in voice_list}
    }

@app.post("/v1/audio/speech")
@app.post("/tts")
async def tts_post(req: TTSRequest):
    text = req.input or req.text
    if not text:
        raise HTTPException(status_code=400, detail="Missing text or input")
    
    voice = req.model or req.voice
    return StreamingResponse(
        get_tts_stream(text, voice, req.rate, req.pitch),
        media_type="audio/mpeg"
    )

@app.get("/v1/audio/speech")
async def tts_get(
    input: Optional[str] = None, 
    text: Optional[str] = None, 
    voice: Optional[str] = "zh-CN-XiaoxiaoNeural", 
    model: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz"
):
    target_text = input or text
    if not target_text:
        raise HTTPException(status_code=400, detail="Missing text or input")
    
    target_voice = model or voice
    return StreamingResponse(
        get_tts_stream(target_text, target_voice, rate, pitch),
        media_type="audio/mpeg"
    )

# 保持 CLI 兼容性，如果 main.ts 仍需要调用
async def run_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    communicate = edge_tts.Communicate(args.text, args.voice, rate=args.rate, pitch=args.pitch)
    await communicate.save(args.output)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_cli())
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)