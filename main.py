import edge_tts
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
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
        
        chunk_count = 0
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
                chunk_count += 1
        
        if chunk_count == 0:
            print(f"Warning: No audio chunks received for voice '{voice}' and text.")
            # 如果没有收到任何音频，可能是音色不支持该语言
            # 但由于已经开始 yield，我们无法更改状态码，只能在服务端记录日志
            # 可以在这里抛出一个异常，以便外部捕获（如果是 StreamingResponse，会导致连接关闭）
            raise HTTPException(status_code=400, detail="Voice mismatch: The selected voice may not support the input language.")
            
    except Exception as e:
        print(f"TTS Stream Error: {e}")
        # 如果是 HTTPException 且我们还没 yield 任何东西，FastAPI 会返回正确错误
        # 但如果是 StreamingResponse 中途抛出，客户端会收到连接异常
        raise e

@app.get("/")
async def root():
    return {"message": "Edge TTS API is running", "docs": "/docs", "voices": "/voices"}

@app.get("/health")
async def health():
    return {"status": "ok"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)