import logging
import secrets
import string
from typing import List

from fastapi import APIRouter
from sqlmodel import Session, select
from starlette.websockets import WebSocket

from app.core.db import engine
from app.models import OneTimeToken, User
from app.modules.face_processing_utils import (anti_spoof_check,
                                               face_recognition_check,
                                               liveness_detection,
                                               validate_face_size)
from app.modules.websocket import (ConnectionManager, FaceIdStep,
                                   get_img_bytes_from_base64,
                                   get_img_ndarray_from_bytes)

router = APIRouter()

logger = logging.getLogger(__name__)


class AuthConnectionManager(ConnectionManager):
    IdType = WebSocket
    steps: List[FaceIdStep] = [
        FaceIdStep(
            value="initial",
            label="Бастапқы жүктеу"
        ),
        FaceIdStep(
            value="antispoof-embeddings",
            label="Ақпараратты тексеру"
        ),
        FaceIdStep(
            value="liveness_check:left",
            label="Сол жаққа қарау"
        ),
        FaceIdStep(
            value="liveness_check:right",
            label="Оң жаққа қарау"
        ),
        FaceIdStep(
            value="auth",
            label="Кіру"
        ),
    ]

    def get_step(self, value: str):
        for i in self.steps:
            if i.value == value:
                return i
        return None


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
                    "message": "Қате қадам.",
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
                analysis1 = anti_spoof_check(img_data)
                if not analysis1["status"]:
                    cxt = {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "data": analysis1,
                        "next_step": manager.steps[2].model_dump(),
                    }
                    if analysis1["message"]:
                        cxt["message"] = analysis1["message"]
                    await manager.send_message(websocket, cxt)
                    continue

                analysis2 = validate_face_size(img_data)
                if not analysis2["status"]:
                    cxt = {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "data": analysis2,
                        "message": analysis2["message"],
                        "next_step": manager.steps[2].model_dump(),
                    }
                    if analysis2["message"]:
                        cxt["message"] = analysis2["message"]
                    await manager.send_message(websocket, cxt)
                    continue

                analysis2 = validate_face_size(img_data)
                await manager.send_message(websocket, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "data": analysis2,
                    "next_step": manager.steps[4].model_dump(),
                })
            elif current_step.value == manager.steps[2].value or current_step.value == manager.steps[3].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)

                required_move = current_step.value.split(":")[1]
                analysis = liveness_detection(img_data, required_move)

                if not analysis["status"]:
                    cxt = {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "data": analysis,
                        "next_step": manager.steps[3].model_dump(),
                    }
                    if analysis["message"]:
                        cxt["message"] = analysis["message"]
                    await manager.send_message(websocket, cxt)
                    continue
                if current_step.value == manager.steps[2].value:
                    await manager.send_message(websocket, {
                        "status": "success",
                        "step": current_step.model_dump(),
                        "data": analysis,
                        "next_step": manager.steps[3].model_dump(),
                    })
                    continue
                elif current_step.value == manager.steps[3].value:
                    await manager.send_message(websocket, {
                        "status": "success",
                        "step": current_step.model_dump(),
                        "data": analysis,
                        "next_step": manager.steps[4].model_dump(),
                    })
                    continue
            elif current_step.value == manager.steps[4].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                analysis = await face_recognition_check(img_data)
                if not analysis["status"]:
                    await manager.send_message(websocket, {
                        "status": "error",
                        "message": analysis['message'],
                        "step": current_step.model_dump(),
                    })
                    continue
                with Session(engine) as session:
                    statement = select(User).where(
                        User.id == analysis['user_id'])
                    found_user__obj: User = session.exec(statement).first()
                    if not found_user__obj:
                        await manager.send_message(websocket, {
                            "status": "error",
                            "message": "Пайдаланушы дерекқордан табылмады.",
                            "step": current_step.model_dump(),
                        })
                        session.close()
                        continue
                    token_obj = OneTimeToken(
                        user_id=found_user__obj.id,
                        token=get_random_string(32),
                        is_used=False,
                    )
                    session.add(token_obj)
                    session.commit()
                    session.refresh(token_obj)
                await manager.send_message(websocket, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "message": "Кіру аяқталды.",
                    "result": {
                        "token": token_obj.token,
                    },
                })

    except Exception as e:
        logger.info(f"Exception: {e}")
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
