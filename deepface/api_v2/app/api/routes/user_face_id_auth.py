import logging
import secrets
import string
from typing import List

import pandas as pd
from app.core.db import engine
from app.models import OneTimeToken, UserFaceId
from app.modules.train_face_id_recognition import auth_face_id_recognition, get_exceptions_type
from app.modules.websocket import (ConnectionManager, FaceIdStep,
                                   get_face_analysis_step, get_face_extras_with_antispoof_step, get_face_validation_data,
                                   get_img_bytes_from_base64,
                                   get_img_ndarray_from_bytes)
from fastapi import APIRouter
from sqlmodel import Session, select
from starlette.websockets import WebSocket

router = APIRouter()

logger = logging.getLogger(__name__)


class AuthConnectionManager(ConnectionManager):
    IdType = WebSocket
    steps: List[FaceIdStep] = [
        FaceIdStep(
            value="initial",
            label="Initial loading"
        ),
        FaceIdStep(
            value="antispoof-embeddings",
            label="Check for embeddings"
        ),
        FaceIdStep(
            value="check_validation",
            label="Validation check"
        ),
        FaceIdStep(
            value="auth",
            label="Authenticate"
        ),
    ]

    def get_step(self, value: str):
        for i in self.steps:
            if i.value == value:
                return i
        return None

    def get_anonymouse_user_id_from_ws(self, websocket: WebSocket):
        return websocket.query_params.get("user_id")


def get_random_string(length: int = 12):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


manager = AuthConnectionManager()


@router.websocket("/user-face-id/auth")
async def websocket_endpoint(websocket: WebSocket):
    conn = manager.active_connections.get(websocket)
    if conn:
        return
    await manager.connect(websocket, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            current_step = manager.get_step(data['step'])
            logger.info(
                f"({websocket}) Received data keys: {data.keys()}. Step={current_step}")
            if current_step is None:
                await manager.send_message(websocket, {
                    "status": "error",
                    "message": "Incorrect step.",
                    "step": current_step,
                })
            elif current_step.value == manager.steps[0].value:
                await manager.send_message(websocket, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "next_step": manager.steps[1].model_dump(),
                })
            elif current_step.value == manager.steps[1].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                try:
                    analysis = get_face_extras_with_antispoof_step(img_data)
                    validated_faces = get_face_validation_data(analysis)
                except Exception as err:
                    _, message = get_exceptions_type(err)
                    await manager.send_message(websocket, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": message,
                    })
                    continue

                res = [{
                    "facial_area": i["facial_area"],
                    "confidence": i["confidence"],
                    "is_real": i["is_real"],
                    "antispoof_score": i["antispoof_score"],
                } for i in analysis]    
                if validated_faces[0]["status"] == "invalid":
                    res[0]["status"] = validated_faces[0]["status"]
                    await manager.send_message(websocket, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "type": "face-size",
                        "message": "Incorrect face size",
                        "data": res,
                        "next_step": manager.steps[2].model_dump(),
                    })
                else:
                    await manager.send_message(websocket, {
                        "status": "success",
                        "step": current_step.model_dump(),
                        "data": res,
                        "next_step": manager.steps[2].model_dump(),
                    })
            elif current_step.value == manager.steps[2].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                try:
                    analysis = get_face_analysis_step(img_data)
                except Exception as err:
                    _, message = get_exceptions_type(err)
                    await manager.send_message(websocket, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": message,
                    })
                    continue
                await manager.send_message(websocket, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "data": analysis,
                    "next_step": manager.steps[3].model_dump(),
                })
            elif current_step.value == manager.steps[3].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                try:
                    result = auth_face_id_recognition(
                        img_data,
                        anti_spoofing=True,
                    )
                except Exception as err:
                    _, message = get_exceptions_type(err)
                    await manager.send_message(websocket, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": message,
                    })
                    continue
                df_list: List[pd.DataFrame] = result['auth']['result']
                combined_df = pd.concat(df_list, ignore_index=True)
                filtered_df = combined_df[combined_df['distance'] < 0.39].nsmallest(
                    1, 'distance')
                print(combined_df)
                if len(filtered_df) == 0:
                    await manager.send_message(websocket, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": "User not found",
                    })
                    continue
                min_threshold_row = filtered_df.loc[filtered_df['distance'].idxmin(
                )]
                with Session(engine) as session:
                    statement = select(UserFaceId).where(
                        UserFaceId.id == min_threshold_row['face_id'])
                    user_face_id_obj: UserFaceId = session.exec(statement).first()
                    if not user_face_id_obj:
                        await manager.send_message(websocket, {
                            "status": "error",
                            "message": "User face id not found.",
                            "step": current_step.model_dump(),
                        })
                        session.close()
                        continue
                    token_obj = OneTimeToken(
                        user_id=user_face_id_obj.user_id,
                        token=get_random_string(32),
                        is_used = False,
                    )
                    session.add(token_obj)
                    session.commit()
                    session.refresh(token_obj)
                await manager.send_message(websocket, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "message": "Auth ended.",
                    "result": {
                        "token": token_obj.token,
                    },
                })

    except Exception as e:
        logger.info(f"Exception: {e}")
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
