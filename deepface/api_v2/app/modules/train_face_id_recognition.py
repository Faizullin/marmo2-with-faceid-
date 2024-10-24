import logging
import os
import pickle
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from app.models import User, UserFaceId

from deepface.commons import image_utils
from deepface.modules import detection, representation, verification
from deepface.modules.recognition import __find_bulk_embeddings

logger = logging.getLogger(__name__)


def get_face_id_storage_dir_path():
    cwd = os.getcwd()
    return Path(cwd).joinpath("face-id-storage")


def generate_storage_dir(path: Path):
    path.mkdir(exist_ok=True)


def generate_input_img_path(user: Union[User, int]):
    id = user if type(user) is int else user.id
    return Path(get_face_id_storage_dir_path()).joinpath("images").joinpath("user_{}".format(id))


def generate_model_path(user: Union[User, int]):
    id = user if type(user) is int else user.id
    return Path(get_face_id_storage_dir_path()).joinpath("models").joinpath("user_{}".format(id))


def get_default_model_cols():
    # required columns for representations
    df_cols = [
        "identity",
        "face_id",
        "hash",
        "embedding",
        "target_x",
        "target_y",
        "target_w",
        "target_h",
    ]
    return df_cols


def get_exceptions_type(err: Exception):
    err_str = str(err)
    if err_str.startswith("Spoof detected in the given image"):
        return "antispoof", "Spoof detected in the given image"
    elif err_str.startswith("Face could not be detected in "):
        return "face_not_detected", "Face could not be detected"
    else:
        return None, "UNknown error"


def save_to_global_model(
    face_obj,
    new_representations,
    silent: bool = False
):
    df_cols = get_default_model_cols()
    global_model_dir_path = Path(get_face_id_storage_dir_path()).joinpath(
        "models").joinpath("global")
    global_model_file_path = global_model_dir_path.joinpath("model1.pkl")
    if not global_model_file_path.exists():
        global_model_dir_path.mkdir(exist_ok=True)
        df_global = pd.DataFrame(columns=df_cols)
        with open(global_model_file_path, "wb") as f:
            pickle.dump(df_global, f)
    else:
        # Load the existing DataFrame from the pickle file
        with open(global_model_file_path, "rb") as f:
            df_global = pickle.load(f)

    # Convert new representations to a DataFrame
    df_new_reps = pd.DataFrame(new_representations)

    # Filter out any rows with the same face_id in the global model
    df_global = df_global[df_global["face_id"] != face_obj.id]

    # Log removed representations if not silent
    removed_count = len(df_new_reps)
    if not silent:
        logger.info(
            f"Removed existing {removed_count} representations in the global model")

    # Append new representations to the global DataFrame
    df_global = pd.concat([df_global, df_new_reps], ignore_index=True)

    # Save the updated DataFrame back to the pickle file
    with open(global_model_file_path, "wb") as f:
        pickle.dump(df_global, f)

    if not silent:
        logger.info(
            f"Global representations updated. Total: {len(df_global)} entries.")


def train_face_id_recognition(
        face_obj: UserFaceId,
        model_name: str = "VGG-Face",
        enforce_detection: bool = True,
        detector_backend: str = "opencv",
        align: bool = True,
        expand_percentage: int = 0,
        threshold: Optional[float] = None,
        normalization: str = "base",
        silent: bool = False,
):
    tic = time.time()

    model_path = Path(face_obj.model_path)

    file_parts = [
        "ds",
        "model",
        model_name,
        "detector",
        detector_backend,
        "aligned" if align else "unaligned",
        "normalization",
        normalization,
        "expand",
        str(expand_percentage),
    ]

    representations = []

    df_cols = get_default_model_cols()

    # Ensure the proper pickle file exists
    if not model_path.exists():
        with open(str(model_path), "wb") as f:
            pickle.dump([], f)

    # Load the representations from the pickle file
    with open(str(model_path), "rb") as f:
        representations = pickle.load(f)

    # check each item of representations list has required keys
    for i, current_representation in enumerate(representations):
        missing_keys = set(df_cols) - set(current_representation.keys())
        if len(missing_keys) > 0:
            raise ValueError(
                f"{i}-th item does not have some required keys - {missing_keys}."
                f"Consider to delete {model_path}"
            )

        # embedded images
    pickled_images = [representation["identity"]
                      for representation in representations]

    # Get the list of images on storage
    image_storage_path = generate_input_img_path(face_obj.user_id)
    storage_images = image_utils.list_images(path=str(image_storage_path))
    logger.info("storage_images: " + str(storage_images))

    if len(storage_images) == 0:
        raise ValueError(f"No item found in {image_storage_path}")

    must_save_pickle = True
    new_images, old_images, replaced_images = set(), set(), set()

    # Enforce data consistency amongst on disk images and pickle file
    new_images = set(storage_images) - \
        set(pickled_images)  # images added to storage
    # images removed from storage
    old_images = set(pickled_images) - set(storage_images)

    # detect replaced images
    for current_representation in representations:
        identity = current_representation["identity"]
        if identity in old_images:
            continue
        alpha_hash = current_representation["hash"]
        beta_hash = image_utils.find_image_hash(identity)
        if alpha_hash != beta_hash:
            logger.debug(
                f"Even though {identity} represented before, it's replaced later.")
            replaced_images.add(identity)

    if not silent and (len(new_images) > 0 or len(old_images) > 0 or len(replaced_images) > 0):
        logger.info(
            f"Found {len(new_images)} newly added image(s)"
            f", {len(old_images)} removed image(s)"
            f", {len(replaced_images)} replaced image(s)."
        )

    # append replaced images into both old and new images. these will be dropped and re-added.
    new_images.update(replaced_images)
    old_images.update(replaced_images)

    # remove old images first
    if len(old_images) > 0:
        representations = [
            rep for rep in representations if rep["identity"] not in old_images]
        must_save_pickle = True

    # find representations for new images
    if len(new_images) > 0:
        new_repr = __find_bulk_embeddings(
            employees=new_images,
            model_name=model_name,
            detector_backend=detector_backend,
            enforce_detection=enforce_detection,
            align=align,
            expand_percentage=expand_percentage,
            normalization=normalization,
            silent=silent,
        )
        for i in new_repr:
            i.update({"face_id": face_obj.id})
        representations += new_repr  # add new images
        must_save_pickle = True

    if must_save_pickle:
        with open(str(model_path), "wb") as f:
            pickle.dump(representations, f)
        if not silent:
            logger.info(
                f"There are now {len(representations)} representations in {model_path}")
        save_to_global_model(face_obj, representations, silent=silent,)

    toc = time.time()
    duration = toc - tic

    # Should we have no representations bailout
    if len(representations) == 0:
        if not silent:
            logger.info(f"find function duration {duration} seconds")
        return []

    stats = {
        "train": {
            "duration": duration,
            "must_save_pickle": must_save_pickle,
        }
    }
    return stats


def verify_face_id_recognition(
        img_path: Union[str, np.ndarray],
        face_obj: UserFaceId,
        model_name: str = "VGG-Face",
        distance_metric: str = "cosine",
        enforce_detection: bool = True,
        detector_backend: str = "opencv",
        align: bool = True,
        expand_percentage: int = 0,
        threshold: Optional[float] = None,
        normalization: str = "base",
        silent: bool = False,
        refresh_database: bool = True,
        anti_spoofing: bool = False,
):
    tic = time.time()

    model_path = Path(face_obj.model_path)

    file_parts = [
        "ds",
        "model",
        model_name,
        "detector",
        detector_backend,
        "aligned" if align else "unaligned",
        "normalization",
        normalization,
        "expand",
        str(expand_percentage),
    ]

    representations = []

    # required columns for representations
    df_cols = get_default_model_cols()

    # Ensure the proper pickle file exists
    if not model_path.exists():
        raise ValueError(f"Passed path {model_path} does not exist!")

    # Load the representations from the pickle file
    with open(str(model_path), "rb") as f:
        representations = pickle.load(f)

    # check each item of representations list has required keys
    for i, current_representation in enumerate(representations):
        missing_keys = set(df_cols) - set(current_representation.keys())
        if len(missing_keys) > 0:
            raise ValueError(
                f"{i}-th item does not have some required keys - {missing_keys}."
                f"Consider to delete {model_path}"
            )

    # ----------------------------
    # now, we got representations for facial database
    df = pd.DataFrame(representations)

    # img path might have more than once face
    source_objs = detection.extract_faces(
        img_path=img_path,
        detector_backend=detector_backend,
        grayscale=False,
        enforce_detection=enforce_detection,
        align=align,
        expand_percentage=expand_percentage,
        anti_spoofing=anti_spoofing,
    )

    resp_obj = []

    for source_obj in source_objs:
        if anti_spoofing is True and source_obj.get("is_real", True) is False:
            raise ValueError("Spoof detected in the given image.")
        source_img = source_obj["face"]
        source_region = source_obj["facial_area"]
        target_embedding_obj = representation.represent(
            img_path=source_img,
            model_name=model_name,
            enforce_detection=enforce_detection,
            detector_backend="skip",
            align=align,
            normalization=normalization,
        )

        target_representation = target_embedding_obj[0]["embedding"]

        result_df = df.copy()  # df will be filtered in each img
        result_df["source_x"] = source_region["x"]
        result_df["source_y"] = source_region["y"]
        result_df["source_w"] = source_region["w"]
        result_df["source_h"] = source_region["h"]

        distances = []
        for _, instance in df.iterrows():
            source_representation = instance["embedding"]
            if source_representation is None:
                # no representation for this image
                distances.append(float("inf"))
                continue

            target_dims = len(list(target_representation))
            source_dims = len(list(source_representation))
            if target_dims != source_dims:
                raise ValueError(
                    "Source and target embeddings must have same dimensions but "
                    + f"{target_dims}:{source_dims}. Model structure may change"
                    + " after pickle created. Delete the {file_name} and re-run."
                )

            distance = verification.find_distance(
                source_representation, target_representation, distance_metric
            )

            distances.append(distance)

            # ---------------------------
        target_threshold = threshold or verification.find_threshold(
            model_name, distance_metric)

        result_df["threshold"] = target_threshold
        result_df["distance"] = distances

        result_df = result_df.drop(columns=["embedding"])
        # pylint: disable=unsubscriptable-object
        result_df = result_df[result_df["distance"] <= target_threshold]
        result_df = result_df.sort_values(
            by=["distance"], ascending=True).reset_index(drop=True)

        resp_obj.append(result_df)

    # -----------------------------------

    toc = time.time()
    duration = toc - tic

    if not silent:
        toc = time.time()
        logger.info(f"find function duration {toc - tic} seconds")

    stats = {
        "auth": {
            "duration": duration,
            "must_save_pickle": False,
            "result": resp_obj,
        }
    }
    return stats


def auth_face_id_recognition(
        img_path: Union[str, np.ndarray],
        model_name: str = "VGG-Face",
        distance_metric: str = "cosine",
        enforce_detection: bool = True,
        detector_backend: str = "opencv",
        align: bool = True,
        expand_percentage: int = 0,
        threshold: Optional[float] = None,
        normalization: str = "base",
        silent: bool = False,
        anti_spoofing: bool = False,
):
    tic = time.time()

    representations = []

    # required columns for representations
    df_cols = get_default_model_cols()
    model_path = Path(get_face_id_storage_dir_path()).joinpath(
        "models").joinpath("global").joinpath("model1.pkl")

    # Ensure the proper pickle file exists
    if not model_path.exists():
        raise ValueError(f"Passed path {model_path} does not exist!")

    # Load the representations from the pickle file
    with open(str(model_path), "rb") as f:
        representations = pickle.load(f)

    # # check each item of representations list has required keys
    # for i, current_representation in enumerate(representations):
    #     missing_keys = set(df_cols) - set(current_representation.keys())
    #     if len(missing_keys) > 0:
    #         raise ValueError(
    #             f"{i}-th item does not have some required keys - {missing_keys}."
    #             f"Consider to delete {model_path}"
    #         )

    # ----------------------------
    # now, we got representations for facial database
    df = pd.DataFrame(representations)

    # img path might have more than once face
    source_objs = detection.extract_faces(
        img_path=img_path,
        detector_backend=detector_backend,
        grayscale=False,
        enforce_detection=enforce_detection,
        align=align,
        expand_percentage=expand_percentage,
        anti_spoofing=anti_spoofing,
    )

    resp_obj = []

    for source_obj in source_objs:
        if anti_spoofing is True and source_obj.get("is_real", True) is False:
            raise ValueError("Spoof detected in the given image.")
        source_img = source_obj["face"]
        source_region = source_obj["facial_area"]
        target_embedding_obj = representation.represent(
            img_path=source_img,
            model_name=model_name,
            enforce_detection=enforce_detection,
            detector_backend="skip",
            align=align,
            normalization=normalization,
        )

        target_representation = target_embedding_obj[0]["embedding"]

        result_df = df.copy()  # df will be filtered in each img
        result_df["source_x"] = source_region["x"]
        result_df["source_y"] = source_region["y"]
        result_df["source_w"] = source_region["w"]
        result_df["source_h"] = source_region["h"]

        distances = []
        for _, instance in df.iterrows():
            source_representation = instance["embedding"]
            if source_representation is None:
                # no representation for this image
                distances.append(float("inf"))
                continue

            target_dims = len(list(target_representation))
            source_dims = len(list(source_representation))
            if target_dims != source_dims:
                raise ValueError(
                    "Source and target embeddings must have same dimensions but "
                    + f"{target_dims}:{source_dims}. Model structure may change"
                    + " after pickle created. Delete the {file_name} and re-run."
                )

            distance = verification.find_distance(
                source_representation, target_representation, distance_metric
            )

            distances.append(distance)

            # ---------------------------
        target_threshold = threshold or verification.find_threshold(
            model_name, distance_metric)

        result_df["threshold"] = target_threshold
        result_df["distance"] = distances

        result_df = result_df.drop(columns=["embedding"])
        # pylint: disable=unsubscriptable-object
        result_df = result_df[result_df["distance"] <= target_threshold]
        result_df = result_df.sort_values(
            by=["distance"], ascending=True).reset_index(drop=True)

        resp_obj.append(result_df)

    # -----------------------------------

    toc = time.time()
    duration = toc - tic

    if not silent:
        toc = time.time()
        logger.info(f"find function duration {toc - tic} seconds")

    stats = {
        "auth": {
            "duration": duration,
            "must_save_pickle": False,
            "result": resp_obj,
        }
    }
    return stats
