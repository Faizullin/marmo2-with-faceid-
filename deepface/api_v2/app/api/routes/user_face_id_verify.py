import logging
import time
from datetime import datetime
from typing import Union, List

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.websockets import WebSocket

from app.api.deps import SessionDep
from app.api.routes.user_face_id_register import get_img_bytes_from_base64, get_img_ndarray_from_bytes, \
    get_face_analysis_step, get_face_extras_with_antispoof_step
from app.core.db import engine
from app.models import User, UserFaceId, UserUpdate
from app.modules.train_face_id_recognition import verify_face_id_recognition

router = APIRouter()

logger = logging.getLogger(__name__)


class FaceIdAuthStep(BaseModel):
    value: str
    label: str


# class ConnectionManager:
#     steps: List[FaceIdAuthStep] = [
#         FaceIdAuthStep(
#             value="move-right",
#             label="Move your face to the right"
#         ),
#         FaceIdAuthStep(
#             value="move-left",
#             label="Move your face to the left"
#         ),
#         FaceIdAuthStep(
#             value="move-forward",
#             label="Face forward"
#         ),
#         FaceIdAuthStep(
#             value="face-id-complete",
#             label="Face id complete"
#         ),
#     ]
#     active_connections: List[WebSocket] = []

class ConnectionManager:
    IdType = Union[str, int]

    def __init__(self):
        self.active_connections: dict = {}  # Dictionary to store connections and their session info

    async def connect(self, websocket: WebSocket, user_id: IdType):
        await websocket.accept()
        self.active_connections[user_id] = {"websocket": websocket, "session_start": time.time()}

    def disconnect(self, user_id: IdType):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: IdType, message: dict):
        websocket = self.active_connections[user_id]["websocket"]
        await websocket.send_json(message)

    def is_session_expired(self, user_id: IdType, max_duration: int = 60) -> bool:
        if user_id not in self.active_connections:
            return True
        session_start = self.active_connections[user_id]["session_start"]
        current_time = time.time()
        return (current_time - session_start) > max_duration

    def reset_session(self, user_id: IdType):
        self.active_connections[user_id]["session_start"] = time.time()


manager = ConnectionManager()


@router.websocket("/user-face-id")
async def websocket_endpoint(websocket: WebSocket, session: SessionDep, ):
    user_obj: User = session.query(User).filter(User.id == 1).first()
    if not user_obj:
        return
    user_face_id_obj: UserFaceId = session.query(UserFaceId).filter(
        UserFaceId.user_id == user_obj.id).first()
    if not user_face_id_obj:
        return
    conn = manager.active_connections.get(user_obj.id)
    if conn:
        return
    session.close()
    await manager.connect(websocket, user_obj.id)

    try:
        while True:
            data = await websocket.receive_json()
            current_step = data['step']
            if current_step not in ["initial", "check_validation", "auth", "antispoof-embeddings"]:
                await manager.send_message(user_obj.id, {
                    "status": "error",
                    "message": "Incorrect step.",
                    "step": current_step,
                })
                break
            if current_step == 'initial':
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step,
                    "next_step": "antispoof-embeddings"
                })
                continue
            elif current_step == "check_validation":
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                analysis = get_face_analysis_step(img_data)
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step,
                    "data": analysis,
                    "next_step": "auth",
                })
            elif current_step == "antispoof-embeddings":
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                analysis = get_face_extras_with_antispoof_step(img_data)
                res = [{
                    "facial_area": i["facial_area"],
                    "confidence": i["confidence"],
                    "is_real": i["is_real"],
                    "antispoof_score": i["antispoof_score"],
                } for i in analysis]
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step,
                    "data": res,
                    "next_step": "check_validation",
                })
            elif current_step == 'auth':
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                result = verify_face_id_recognition(
                    img_data,
                    face_obj=user_face_id_obj,
                    anti_spoofing=True,
                )
                df_list: List[pd.DataFrame] = result['auth']['result']
                # records = [i.to_dict(orient='records') for i in df_list]
                combined_df = pd.concat(df_list, ignore_index=True)
                print(combined_df)
                filtered_df = combined_df[combined_df['distance'] < 0.39].nsmallest(1, 'distance')
                print(filtered_df)
                min_threshold_row = filtered_df.loc[filtered_df['distance'].idxmin()]
                print(min_threshold_row)

                is_verified = bool(min_threshold_row['face_id'] == user_face_id_obj.id)
                with Session(engine) as session:
                    statement = select(User).where(User.id == user_face_id_obj.user_id)
                    user_obj = session.exec(statement).first()
                    user_obj.face_id_verified = True
                    user_obj.face_id_verified_at = datetime.now()
                    session.add(user_obj)
                    session.commit()
                    session.refresh(user_obj)
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step,
                    "message": "Auth ended.",
                    "result": {
                        "verified": is_verified,
                    },
                })


    except Exception as e:
        logger.info(f"Connection closed: {e}")
        manager.disconnect(user_obj.id)
    finally:
        manager.disconnect(user_obj.id)
