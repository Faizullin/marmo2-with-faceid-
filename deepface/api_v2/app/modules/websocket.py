import base64
import io
import time
from typing import Union

import numpy as np
from PIL import Image
from pydantic import BaseModel
from starlette.websockets import WebSocket

from deepface import DeepFace


def get_face_analysis_step(img: np.ndarray):
    face_analysis = DeepFace.analyze(
        img, actions=['emotion'], anti_spoofing=True, )
    return face_analysis


def get_face_extras_with_antispoof_step(img: np.ndarray):
    face_analysis = DeepFace.extract_faces(
        img,
        anti_spoofing=True,
        enforce_detection=False,
    )
    return face_analysis


def get_img_bytes_from_base64(input_img: str):
    base64_str = input_img.split(",")[1]
    return base64.b64decode(base64_str)


def get_img_ndarray_from_bytes(input_img: bytes):
    img_data = Image.open(io.BytesIO(input_img))
    img_data = np.array(img_data)
    return img_data


# Define the min and max face size you want to validate
MIN_FACE_SIZE = 210  # Minimum width/height in pixels
MAX_FACE_SIZE = 300  # Maximum width/height in pixels


def get_face_validation_data(faces):
    validated_faces = []
    for face_data in faces:
        face = face_data["face"]  # The extracted face image as a numpy array
        # The bounding box of the face (x, y, width, height)
        region = face_data["facial_area"]

        face_width = region["w"]
        face_height = region["h"]

        # Check if face size is within the defined range
        if MIN_FACE_SIZE <= face_width <= MAX_FACE_SIZE and MIN_FACE_SIZE <= face_height <= MAX_FACE_SIZE:
            validated_faces.append({"status": "valid", "facial_area": region})
        else:
            validated_faces.append(
                {"status": "invalid", "facial_area": region})
    return validated_faces


class FaceIdStep(BaseModel):
    value: str
    label: str


class ConnectionManager:
    IdType = Union[str, int]

    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: IdType):
        await websocket.accept()
        self.active_connections[user_id] = {
            "websocket": websocket, "session_start": time.time()}

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
