import traceback
import sys

try:
    from ai_service.engine import AIEngine
    from ai_service.voice_pipeline import VoicePipeline
    print("Imports passed")
    e = AIEngine()
    print("AIEngine passed")
    v = VoicePipeline(e)
    print("VoicePipeline passed")
except Exception as ex:
    print("ERROR:")
    traceback.print_exc()
