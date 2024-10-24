import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, WebSocket, Query, HTTPException, Depends
from sqlmodel import Session, select
from starlette import status

from app.api.deps import SessionDep
from app.core.db import engine
from app.models import User, UserFaceId
from app.modules.face_processing_utils import (anti_spoof_check,
                                               liveness_detection,
                                               train_new_face,
                                               validate_face_size, retrain_all_faces, add_face_to_global)
from app.modules.storage import storage
from app.modules.websocket import (ConnectionManager, FaceIdStep,
                                   get_img_bytes_from_base64,
                                   get_img_ndarray_from_bytes)

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
            value="register",
            label="Тіркеу"
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
                f"({websocket}) Received data keys: {data.keys()}. Step={current_step}")
            if current_step is None:
                await manager.send_message(user_obj.id, {
                    "status": "error",
                    "message": "Қате қадам.",
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
                    await manager.send_message(user_obj.id, cxt)
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
                    await manager.send_message(user_obj.id, cxt)
                    continue

                await manager.send_message(user_obj.id, {
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
                    await manager.send_message(user_obj.id, cxt)
                    continue
                if current_step.value == manager.steps[2].value:
                    await manager.send_message(user_obj.id, {
                        "status": "success",
                        "step": current_step.model_dump(),
                        "data": analysis,
                        "next_step": manager.steps[3].model_dump(),
                    })
                    continue
                elif current_step.value == manager.steps[3].value:
                    await manager.send_message(user_obj.id, {
                        "status": "success",
                        "step": current_step.model_dump(),
                        "data": analysis,
                        "next_step": manager.steps[4].model_dump(),
                    })
                    continue
            elif current_step.value == manager.steps[4].value:
                img_base64_data = get_img_bytes_from_base64(data['image'])
                img_data = get_img_ndarray_from_bytes(img_base64_data)
                # await save_input_image(current_step.value, generate_input_img_path(user_obj), img_base64_data)
                with Session(engine) as session:
                    user_face_id_obj = session.exec(
                        select(UserFaceId).filter_by(user_id=user_obj.id)
                    ).first()
                    model_path = storage.get_face_id_storage_models_dir_path().joinpath(
                        f"user_{user_obj.id}_model.pkl")
                    if not user_face_id_obj:
                        user_face_id_obj = UserFaceId(
                            user_id=user_obj.id,
                            stats={},
                            model_path=str(model_path),
                        )
                        session.add(user_face_id_obj)
                    else:
                        user_face_id_obj.model_path = model_path
                    session.commit()
                    session.refresh(user_face_id_obj)
                analysis = await train_new_face(img_data, face_obj=user_face_id_obj)
                if not analysis["status"]:
                    await manager.send_message(user_obj.id, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": analysis["message"],
                        "data": analysis,
                    })
                    continue

                analysis_global = await add_face_to_global(
                    face_obj=user_face_id_obj,
                )
                if not analysis_global["status"]:
                    await manager.send_message(user_obj.id, {
                        "status": "error",
                        "step": current_step.model_dump(),
                        "message": analysis_global["message"],
                        "data": analysis_global,
                    })
                    continue

                await manager.send_message(user_obj.id, {
                    "status": "success",
                    "step": current_step.model_dump(),
                    "message": "Тіркеу аяқталды.",
                    "data": analysis,
                })

    except Exception as e:
        logger.info(f"Exception: {str(e)}")
        manager.disconnect(user_obj.id)
    finally:
        manager.disconnect(user_obj.id)


def get_and_validate_auth_key(key: str = Query()):
    if key != "admin-sender-key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials", )
    return key


@router.get("/user-face-id/retrain")
async def retrain_endpoint(session: SessionDep, _=Depends(get_and_validate_auth_key)):
    user_face_id_list = session.exec(select(UserFaceId)).all()
    session.close()
    analysis = await retrain_all_faces(user_face_id_list)
    return analysis
