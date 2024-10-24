import pickle
from pathlib import Path
from typing import List

import face_recognition
import numpy as np
import pandas as pd

from app.models import UserFaceId
from app.modules.ml_weights import face_detector, spoofing_detector
from app.modules.storage import storage


def get_no_face_error():
    return {
        "status": False,
        "message": "Бет анықталмады",
        "code": "no_face_error",
    }


def get_face_number_error():
    return {
        "status": False,
        "message": "Бірнеше бет анықталды",
        "code": "face_number_gt_1_error",
    }


def validate_face_size(image: np.ndarray, min_face_size=(140, 140), max_face_size=(280, 280)):
    try:
        face_locations = face_recognition.face_locations(image)
        if len(face_locations) == 0:
            return get_no_face_error()
        elif len(face_locations) > 1:
            return get_face_number_error()

        top, right, bottom, left = face_locations[0]
        face_width = right - left
        face_height = bottom - top

        if face_width < min_face_size[0] or face_height < min_face_size[1]:
            return {
                "status": False,
                "message": "Өлшемі - тым кіші",
            }
        if face_width > max_face_size[0] or face_height > max_face_size[1]:
            return {
                "status": False,
                "message": "Өлшемі - тым үлкен",
            }

        return {
            "status": True,
            "message": "Жарамды сурет",
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"қате: {str(e)}"
        }


def get_face_direction(landmarks: dict):
    """
    Determine the direction of the face based on the position of key facial landmarks.
    For simplicity, this function focuses on the relative positions of eyes and nose.
    """
    left_eye = np.mean(landmarks['left_eye'],
                       axis=0)  # Get the center of the left eye
    # Get the center of the right eye
    right_eye = np.mean(landmarks['right_eye'], axis=0)
    # Get the center of the nose bridge
    nose = np.mean(landmarks['nose_bridge'], axis=0)

    # Calculate horizontal and vertical shifts
    eye_dist_x = right_eye[0] - left_eye[0]  # Horizontal distance between eyes
    # Relative nose position
    nose_eye_dist_x = nose[0] - (left_eye[0] + right_eye[0]) / 2

    # Simple thresholding to determine the direction
    if nose_eye_dist_x > 0.1 * eye_dist_x:  # Nose shifted right relative to eyes
        return "left"
    elif nose_eye_dist_x < -0.1 * eye_dist_x:  # Nose shifted left relative to eyes
        return "right"
    else:  # Nose is centered between the eyes
        return "forward"


# Liveness detection function
def liveness_detection(image, required_move):
    """
    Detects if the face in the image is moving in the required direction (left, right, forward).
    Uses face landmarks for validation and compares the current face direction with the required move.
    """
    try:
        # Detect facial landmarks
        face_landmarks_list = face_recognition.face_landmarks(image)

        if len(face_landmarks_list) == 0:
            return False, "No face detected."

        if len(face_landmarks_list) > 1:
            return False, "Multiple faces detected. Only one face is allowed."

        # Retrieve the landmarks of the detected face
        face_landmarks = face_landmarks_list[0]

        # Get the current direction of the face
        current_direction = get_face_direction(face_landmarks)

        # Compare current direction with the required movement
        if current_direction == required_move:
            return {
                "status": True,
                "message": f"Liveness detected: Moved {current_direction} as required.",
            }
        else:
            return {
                "status": False,
                "message": f"Incorrect movement. Expected {required_move}, but detected {current_direction}.",
            }

    except Exception as e:
        return {
            "status": False,
            "message": f"Error in liveness detection: {str(e)}"
        }


def anti_spoof_check(image: np.ndarray):
    """
    Perform anti-spoofing check to verify if the face is real or fake.
    """
    try:
        faces = face_detector(image).respond_data

        if len(faces) == 0:
            return get_no_face_error()
        elif len(faces) > 1:
            return get_face_number_error()

        boxes = [box.tolist() for box, _, _ in faces]
        spoof_msg = spoofing_detector(boxes, image)
        spoofs = spoof_msg.respond_data
        respond = {
            "nums": len(spoofs),
            "is_reals": [bool(is_spoof) for is_spoof, _ in spoofs],
            "scores": [round(float(score), 4) for _, score in spoofs],
            "boxes": boxes
        }
        status = all([i for i in respond['is_reals']])
        return {
            "status": status,
            "data": respond,
            "message": "Спуфинг анықталды." if not status else None,
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"қате: {str(e)}",
        }


async def face_recognition_check(image: np.ndarray):
    try:
        new_user_face_encodings = face_recognition.face_encodings(image)
        if len(new_user_face_encodings) != 1:
            return get_face_number_error()

        global_modal_path = storage.get_global_model_file_path()
        with open(global_modal_path, "rb") as file:
            stored_model_data: pd.DataFrame = pickle.load(file)

        matches = face_recognition.compare_faces(
            list(stored_model_data["encodings"]), new_user_face_encodings[0])
        if True in matches:
            user_id = stored_model_data["user_id"][matches.index(True)]
            return {
                "status": True,
                "user_id": user_id,
            }
        else:
            return {
                "status": False,
                "message": "Белгісіз қолданушы.",
            }
    except Exception as e:
        return {
            "status": False,
            "message": f"қате: {str(e)}",
        }


async def add_face_to_global(face_obj: UserFaceId):
    try:
        user_model_path = Path(face_obj.model_path)
        with open(user_model_path, "rb") as file:
            new_entry = pickle.load(file)
        global_model_path = storage.get_global_model_file_path()
        with open(global_model_path, "rb") as file:
            stored_model_data = pickle.load(file)

        new_stored_model_data = stored_model_data[stored_model_data["user_id"] != face_obj.user_id]

        new_stored_model_data = pd.concat(
            [new_stored_model_data, new_entry], ignore_index=True)

        with open(global_model_path, "wb") as file:
            pickle.dump(new_stored_model_data, file)

        return {
            "status": True,
            "message": "Жаңа бет биометриясы қосылды.",
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"қате: {str(e)}",
        }


async def train_new_face(image, face_obj: UserFaceId):
    try:
        new_user_face_encodings = face_recognition.face_encodings(image)
        if len(new_user_face_encodings) == 0:
            return get_no_face_error()

        model_path = Path(face_obj.model_path)
        new_stored_model_data = pd.DataFrame(
            {"encodings": [], "user_id": [], })
        new_entry = pd.DataFrame(
            {"encodings": [new_user_face_encodings[0]], "user_id": [face_obj.user_id], })
        new_stored_model_data = pd.concat(
            [new_stored_model_data, new_entry], ignore_index=True)

        with open(str(model_path), "wb") as file:
            pickle.dump(new_stored_model_data, file)

        return {
            "status": True,
            "message": "Жаңа бет биометриясы қосылды.",
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"қате: {str(e)}",
        }


async def retrain_all_faces(
        face_list: List[UserFaceId],
):
    try:
        new_stored_model_data = pd.DataFrame(
            {"encodings": [], "user_id": [], })
        for face_item_obj in face_list:
            with open(str(face_item_obj.model_path), "rb") as file:
                new_entry = pickle.load(file)
                new_stored_model_data = pd.concat(
                    [new_stored_model_data, new_entry], ignore_index=True)

        global_model_path = storage.get_global_model_file_path()
        with open(str(global_model_path), "wb") as file:
            pickle.dump(new_stored_model_data, file)

        return {
            "status": True,
            "message": "Faces have been retrained.",
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"Error in face training: {str(e)}",
        }
