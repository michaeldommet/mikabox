"""
MikaBox Backend — FastAPI Application
======================================

Main entry point for the MikaBox server.
Serves the REST API, WebSocket hub, and AI voice pipeline.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import init_db, get_db
from .models import Content
from .routers import auth, devices, content, controls, usage, profiles, memory
from .services import device_service

logger = logging.getLogger("mikabox.server")

# AI engine (lazy-loaded)
_ai_engine = None
_voice_pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║     🎵 MikaBox Server Starting 🎵    ║")
    logger.info("╚══════════════════════════════════════╝")

    await init_db()
    logger.info("Database initialized.")

    # Load AI engine
    global _ai_engine, _voice_pipeline
    try:
        from ai_service.engine import AIEngine
        from ai_service.voice_pipeline import VoicePipeline

        _ai_engine = AIEngine()
        _voice_pipeline = VoicePipeline(_ai_engine)
        logger.info("AI engine loaded.")
    except Exception as exc:
        logger.warning("AI engine not available: %s", exc)

    yield

    # Shutdown
    if _ai_engine:
        _ai_engine.shutdown()
    logger.info("Server shut down.")


app = FastAPI(
    title="MikaBox API",
    description="Backend API for the MikaBox kids smart speaker.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(content.router)
app.include_router(controls.router)
app.include_router(usage.router)
app.include_router(profiles.router)
app.include_router(memory.router)


# ── Health Check ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "ai_ready": _ai_engine is not None and _ai_engine.is_ready,
    }


# ── Voice Processing Endpoint ────────────────────────────────────────

@app.post("/api/voice/process")
async def process_voice(
    audio: UploadFile = File(...),
    device_id: str = Form(""),
    profile_id: str = Form("default"),
    db: AsyncSession = Depends(get_db),
):
    """
    Process voice audio from the MikaBox device.
    Runs STT → Gemma 4 NLU → returns command result.
    """
    if not _voice_pipeline:
        return {"action": "none", "message": "AI service not available."}

    audio_bytes = await audio.read()

    # Build default profile context
    profile = {"name": "buddy", "age": 5, "id": profile_id}

    # Resolve actual child profile from database
    from .models import Device, ChildProfile
    child = None
    if profile_id == "default" and device_id:
        device_obj = await db.scalar(select(Device).where(Device.device_id == device_id))
        if device_obj:
            child = await db.scalar(select(ChildProfile).where(ChildProfile.user_id == device_obj.user_id))
    elif profile_id != "default":
        child = await db.scalar(select(ChildProfile).where(ChildProfile.id == profile_id))

    if child:
        profile_id = str(child.id)
        profile = {"name": child.name, "age": child.age, "id": profile_id}

    # Fetch available content to give LLM context
    result_db = await db.execute(select(Content).order_by(Content.title))
    items = result_db.scalars().all()
    # Format a string of available content
    catalog_text = ", ".join([f"'{c.title}' (ID: {c.id})" for c in items])

    # Extract text early for RAG
    search_text = _voice_pipeline._speech_to_text(audio_bytes)

    # Lightweight RAG search
    memory_facts_str = "None yet."
    from .models import MemoryFact
    import json
    from ai_service.embeddings import embedding_service

    mem_result = await db.execute(
        select(MemoryFact).where(MemoryFact.profile_id == profile_id)
    )
    all_facts = mem_result.scalars().all()

    if all_facts:
        if search_text and embedding_service.is_available:
            query_vector = embedding_service.encode(search_text)
            scored_facts = []
            for f in all_facts:
                if f.embedding:
                    try:
                        vec = json.loads(f.embedding)
                        score = embedding_service.cosine_similarity(query_vector, vec)
                        scored_facts.append((score, f))
                    except Exception:
                        scored_facts.append((0.0, f))
                else:
                    scored_facts.append((0.0, f))
            # Sort by cosine similarity
            scored_facts.sort(key=lambda x: x[0], reverse=True)
            top_facts = [f.fact for score, f in scored_facts[:2]]
        else:
            # Fallback to recent 2 facts
            all_facts.sort(key=lambda x: x.created_at, reverse=True)
            top_facts = [f.fact for f in all_facts[:2]]
            
        memory_facts_str = "\n".join([f"- {fact}" for fact in top_facts])

    result = await _voice_pipeline.process_audio(
        audio_bytes=audio_bytes,
        profile=profile,
        available_content=catalog_text,
        memory_facts=memory_facts_str,
    )

    # Log search queries if one occurred during this turn
    searched_query = result.get("searched_query")
    safety_alert = result.get("safety_alert")
    remembered_fact = result.get("remembered_fact")
    
    if searched_query or safety_alert or remembered_fact:
        import json
        from .models import UsageLog
        
        if searched_query:
            db.add(UsageLog(
                profile_id=profile_id,
                event_type="web_search",
                metadata_json=json.dumps({"query": searched_query}),
            ))
            
        if safety_alert:
            db.add(UsageLog(
                profile_id=profile_id,
                event_type="safety_alert",
                metadata_json=json.dumps({"reason": safety_alert}),
            ))
            # Instantly broadcast the alert to the web dashboard
            await device_service.broadcast_device_state(device_id, {"safety_alert": safety_alert})

        remembered_fact = result.get("remembered_fact")
        if remembered_fact:
            embedding_json = None
            if embedding_service.is_available:
                vec = embedding_service.encode(remembered_fact)
                embedding_json = json.dumps(vec)
                
            db.add(MemoryFact(
                profile_id=profile_id,
                fact=remembered_fact,
                embedding=embedding_json
            ))

        await db.commit()

    return result


# ── Device WebSocket ──────────────────────────────────────────────────

@app.websocket("/ws/device")
async def device_websocket(ws: WebSocket, device_id: str = ""):
    """
    WebSocket endpoint for MikaBox device connections.
    Handles real-time state sync and command relay.
    """
    await ws.accept()
    await device_service.register_device(device_id, ws)

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "state":
                # Broadcast device state to watching apps
                await device_service.broadcast_device_state(device_id, data.get("data", {}))
            elif msg_type == "usage":
                # Log usage event
                pass  # handled via HTTP

    except WebSocketDisconnect:
        await device_service.unregister_device(device_id)


# ── Companion App WebSocket ──────────────────────────────────────────

@app.websocket("/ws/app")
async def app_websocket(ws: WebSocket, device_id: str = ""):
    """
    WebSocket endpoint for companion app connections.
    Receives real-time device state updates.
    """
    await ws.accept()
    await device_service.register_app_watcher(device_id, ws)

    try:
        while True:
            data = await ws.receive_json()
            cmd = data.get("command", "")
            payload = data.get("payload", {})

            # Relay command to device
            await device_service.send_to_device(device_id, cmd, payload)

    except WebSocketDisconnect:
        await device_service.unregister_app_watcher(device_id, ws)
