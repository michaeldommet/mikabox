import asyncio
import traceback

async def run():
    try:
        from ai_service.engine import AIEngine
        from ai_service.voice_pipeline import VoicePipeline

        _ai_engine = AIEngine()
        _voice_pipeline = VoicePipeline(_ai_engine)
        print("AI engine loaded.")
    except Exception as exc:
        print("AI engine not available:")
        traceback.print_exc()

asyncio.run(run())
