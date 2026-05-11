from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid

from .database import init_db, SessionLocal, get_db
from .models import Argument, Claim, Fallacy, ClaimEdge, VeracityEvent, ManifoldSnapshot
from .services import VeracityAuditor, FallacyDetector, LLMAnalyzer, ManifoldCalculator

app = FastAPI(title="Fallacy Map API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class CreateArgumentRequest(BaseModel):
    title: str
    source_text: str

class AnalyzeRequest(BaseModel):
    argument_id: str
    chunk: str

class FallacyResult(BaseModel):
    fallacy_type: str
    claim_text: str
    magnitude: float
    persistence: float
    V_cost: float
    V_active: float
    bypass_triggered: bool
    inverion_triggered: bool

class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]

@app.get("/")
async def root():
    return {"message": "Fallacy Map API", "version": "1.0.0"}

@app.post("/arguments")
async def create_argument(req: CreateArgumentRequest):
    db = SessionLocal()
    try:
        argument = Argument(
            title=req.title,
            source_text=req.source_text
        )
        db.add(argument)
        db.commit()
        db.refresh(argument)
        return {"id": argument.id, "title": argument.title, "V_active": argument.V_active}
    finally:
        db.close()

@app.get("/arguments/{argument_id}")
async def get_argument(argument_id: str):
    db = SessionLocal()
    try:
        argument = db.query(Argument).filter(Argument.id == argument_id).first()
        if not argument:
            raise HTTPException(status_code=404, message="Argument not found")
        
        claims = db.query(Claim).filter(Claim.argument_id == argument_id).all()
        fallacies = db.query(Fallacy).filter(Fallacy.claim_id.in_([c.id for c in claims])).all() if claims else []
        
        return {
            "id": argument.id,
            "title": argument.title,
            "source_text": argument.source_text,
            "V_active": argument.V_active,
            "V_initial": argument.V_initial,
            "inverion_triggered": argument.inverion_triggered,
            "root_fallacy_id": argument.root_fallacy_id,
            "bypass_count": argument.bypass_count,
            "claims": [{"id": c.id, "text": c.text, "is_conclusion": c.is_conclusion} for c in claims],
            "fallacies": [{
                "id": f.id,
                "fallacy_type": f.fallacy_type,
                "magnitude": f.magnitude,
                "persistence": f.persistence
            } for f in fallacies]
        }
    finally:
        db.close()

@app.post("/analyze")
async def analyze_chunk(argument_id: str, text: str):
    db = SessionLocal()
    try:
        argument = db.query(Argument).filter(Argument.id == argument_id).first()
        if not argument:
            raise HTTPException(status_code=404, message="Argument not found")
        
        if argument.inverion_triggered:
            return {"error": "Inverion Divide triggered", "V_active": 0}
        
        auditor = VeracityAuditor(db, argument_id)
        analyzer = LLMAnalyzer()
        detector = FallacyDetector()
        
        claims = db.query(Claim).filter(Claim.argument_id == argument_id).order_by(Claim.created_at).all()
        context = [{"type": f.fallacy_type, "text": f.fallacy_type} for f in db.query(Fallacy).filter(
            Fallacy.claim_id.in_([c.id for c in claims])
        ).all()][:5]
        
        fallacies_found = analyzer.analyze_sync(text, context)
        
        results = []
        for f in fallacies_found:
            if "error" in f:
                continue
                
            claim = Claim(
                argument_id=argument_id,
                text=f.get('claim_text', text)
            )
            db.add(claim)
            db.commit()
            db.refresh(claim)
            
            info = detector.get_fallacy_info(f.get('fallacy_type', ''))
            base_weight = info.get('base_weight', 0.5) if info else 0.5
            magnitude = f.get('magnitude', 0.5) * base_weight
            persistence = f.get('persistence', 0.5)
            
            v_result = auditor.process_fallacy(
                fallacy_type=f.get('fallacy_type', 'unknown'),
                magnitude=magnitude,
                persistence=persistence,
                claim_id=claim.id
            )
            
            fallacy = Fallacy(
                claim_id=claim.id,
                fallacy_type=f.get('fallacy_type', 'unknown'),
                magnitude=magnitude,
                persistence=persistence,
                depth=f.get('depth', 0)
            )
            db.add(fallacy)
            db.commit()
            
            if v_result.get('inverion_triggered'):
                auditor.set_root_fallacy(fallacy.id)
            
            results.append({
                "fallacy_type": f.get('fallacy_type'),
                "claim_text": f.get('claim_text'),
                "magnitude": magnitude,
                "persistence": persistence,
                "V_cost": v_result.get('V_cost', 0),
                "V_active": v_result.get('V_after', auditor.V_active),
                "bypass_triggered": v_result.get('bypass_triggered', False),
                "inverion_triggered": v_result.get('inverion_triggered', False)
            })
        
        return {"fallacies": results, "V_active": auditor.V_active}
    finally:
        db.close()

@app.get("/veracity/{argument_id}")
async def get_veracity_state(argument_id: str):
    db = SessionLocal()
    try:
        auditor = VeracityAuditor(db, argument_id)
        return auditor.get_state()
    finally:
        db.close()

@app.get("/snapshots/{argument_id}")
async def get_snapshots(argument_id: str):
    db = SessionLocal()
    try:
        snapshots = db.query(ManifoldSnapshot).filter(
            ManifoldSnapshot.argument_id == argument_id
        ).order_by(ManifoldSnapshot.timestamp).all()
        return [{
            "id": s.id,
            "timestamp": s.timestamp.isoformat(),
            "integrity_score": s.integrity_score
        } for s in snapshots]
    finally:
        db.close()

@app.websocket("/ws/{argument_id}")
async def websocket_endpoint(websocket: WebSocket, argument_id: str):
    await websocket.accept()
    db = SessionLocal()
    try:
        argument = db.query(Argument).filter(Argument.id == argument_id).first()
        if not argument:
            await websocket.close(code=4004)
            return
        
        auditor = VeracityAuditor(db, argument_id)
        manifold = ManifoldCalculator()
        
        await websocket.send_json({
            "type": "connected",
            "V_active": auditor.V_active
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "analyze_chunk":
                text = message.get("text", "")
                
                if argument.inverion_triggered:
                    await websocket.send_json({
                        "type": "inverion_triggered",
                        "V_active": 0
                    })
                    continue
                
                analyzer = LLMAnalyzer()
                detector = FallacyDetector()
                
                claims = db.query(Claim).filter(Claim.argument_id == argument_id).all()
                context = [{"type": f.fallacy_type, "text": f.fallacy_type} for f in db.query(Fallacy).filter(
                    Fallacy.claim_id.in_([c.id for c in claims])
                ).all()][:5]
                
                fallacies_found = analyzer.analyze_sync(text, context)
                
                for f in fallacies_found:
                    if "error" in f:
                        continue
                    
                    claim = Claim(argument_id=argument_id, text=f.get('claim_text', text))
                    db.add(claim)
                    db.commit()
                    db.refresh(claim)
                    
                    info = detector.get_fallacy_info(f.get('fallacy_type', ''))
                    base_weight = info.get('base_weight', 0.5) if info else 0.5
                    magnitude = f.get('magnitude', 0.5) * base_weight
                    persistence = f.get('persistence', 0.5)
                    
                    v_result = auditor.process_fallacy(
                        fallacy_type=f.get('fallacy_type', 'unknown'),
                        magnitude=magnitude,
                        persistence=persistence,
                        claim_id=claim.id
                    )
                    
                    fallacy = Fallacy(
                        claim_id=claim.id,
                        fallacy_type=f.get('fallacy_type', 'unknown'),
                        magnitude=magnitude,
                        persistence=persistence
                    )
                    db.add(fallacy)
                    db.commit()
                    db.refresh(fallacy)
                    
                    if v_result.get('inverion_triggered'):
                        auditor.set_root_fallacy(fallacy.id)
                    
                    pos = (claim.id[-4:].encode().hex()[:3], 0, claim.id[-8:].encode().hex()[:3])
                    manifold.add_fallacy(pos, magnitude, f.get('fallacy_type', 'well'))
                    
                    await websocket.send_json({
                        "type": "fallacy_detected",
                        "fallacy": {
                            "id": fallacy.id,
                            "type": f.get('fallacy_type'),
                            "claim_text": f.get('claim_text'),
                            "magnitude": magnitude,
                            "persistence": persistence
                        },
                        "V_active": v_result.get('V_after', 0),
                        "V_cost": v_result.get('V_cost', 0),
                        "bypass_triggered": v_result.get('bypass_triggered', False),
                        "inverion_triggered": v_result.get('inverion_triggered', False),
                        "mesh_update": manifold.get_heatmap_values()
                    })
                
                await websocket.send_json({
                    "type": "chunk_complete",
                    "V_active": auditor.V_active
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)