import logging
from pathlib import Path
from typing import List, Union

from app.api.deps import SessionDep
from app.core.db import engine
from app.models import User, UserFaceId
from app.modules.train_face_id_recognition import (generate_input_img_path,
                                                   generate_model_path, get_exceptions_type,
                                                   train_face_id_recognition)
from app.modules.websocket import ConnectionManager, FaceIdStep, get_face_analysis_step, get_face_extras_with_antispoof_step, get_img_bytes_from_base64, get_img_ndarray_from_bytes
from fastapi import APIRouter, WebSocket
from sqlmodel import Session

router = APIRouter()

logger = logging.getLogger(__name__)




async def save_input_image(step: str, path: Path, input_img: bytes):
    path.mkdir(exist_ok=True)
    file_to_save = path.joinpath("img_{}.png".format(step))
    with open(file_to_save, "wb+") as f:
        f.write(input_img)


class AuthConnectionManager(ConnectionManager):
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
            value="register",
            label="Register"
        ),
    ]

    def get_step(self, value: str):
        for i in self.steps:
            if i.value == value:
                return i
        return None


manager = AuthConnectionManager()


@router.websocket("/user-face-id/register")
async def websocket_endpoint(websocket: WebSocket, session: SessionDep, user_id: int):
    user_obj: User = session.query(User).filter(User.id == user_id).first()
    if not user_obj:
        return
    conn = manager.active_connections.get(user_obj.id)
    if conn:
        return
    session.close()
    await manager.connect(websocket, user_obj.id)
    try:
        while True:
            data = await websocket.receive_json()
            current_step = manager.get_step(data['step'])
            logger.info(
                f"({user_obj.id}) Received data keys: {data.keys()}. Step={current_step}")
            if current_step is None:
                await manager.send_message(user_obj.id, {
                    "status": "error",
                    "message": "Incorrect step.",
                    "step": current_step,
                })
            elif current_step.value == manager.steps[0].value:
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "next_step": manager.steps[1].model_dump(),
                })
            elif current_step.value == manager.steps[1].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                try:
                    analysis = get_face_extras_with_antispoof_step(img_data)
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
                await save_input_image(current_step.value, generate_input_img_path(user_obj), img_base64_data)
                await manager.send_message(user_obj.id, {
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
                await save_input_image(current_step.value, generate_input_img_path(user_obj), img_base64_data)
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "data": analysis,
                    "next_step": manager.steps[3].model_dump(),
                })
            elif current_step.value == manager.steps[3].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                await save_input_image(current_step.value, generate_input_img_path(user_obj), img_base64_data)
                with Session(engine) as session:
                    user_face_id_obj: UserFaceId = session.query(UserFaceId).filter(
                        UserFaceId.user_id == user_obj.id).first()
                    model_path = generate_model_path(user_obj)
                    model_path.mkdir(exist_ok=True)
                    model_path = str(model_path.joinpath("model1.pkl"))
                    if not user_face_id_obj:
                        user_face_id_obj = UserFaceId(
                            user_id=user_obj.id,
                            stats={},
                            model_path=model_path,
                        )
                        session.add(user_face_id_obj)
                    else:
                        user_face_id_obj.model_path = model_path
                    session.commit()
                    session.refresh(user_face_id_obj)
                result = train_face_id_recognition(
                    face_obj=user_face_id_obj,
                )
                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "message": "Train ended.",
                    "result": result,
                })

    except Exception as e:
        logger.info(f"Connection closed: {e}")
        manager.disconnect(user_obj.id)
    finally:
        manager.disconnect(user_obj.id)
