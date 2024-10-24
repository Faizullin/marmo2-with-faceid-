import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.main import api_router
from app.core.config import settings
from app.modules.antispoof.library.task_manager import stop_worker
from app.modules.ml_weights import (load_models)
from app.modules.ml_weights import face_detector, spoofing_detector


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(_):
    await load_models()
    face_detector.start()
    spoofing_detector.start()
    yield
    signal.signal(signal.SIGINT, lambda sig, frame: stop_worker(
        face_detector, spoofing_detector))


app_args = dict()
if settings.DEBUG:
    app_args.update({
        "openapi_url": f"{settings.API_V1_STR}/openapi.json",
    })

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    # **app_args,
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# import numpy as np
# from fastapi import FastAPI, HTTPException, Depends
# from app.modules.antispoof.library.utils.api import image_read
# @app.post("/spoofing",
#           summary="Detect spoofing face",
#           description="Detect spoofing face from image and face's box")
# def anti_spoofing(image: np.ndarray = Depends(image_read)):
#     faces = face_detector(image).respond_data

#     if len(faces) <= 0:
#         raise HTTPException(400, "Can't detect any face in image.")

#     boxes = [box.tolist() for box, _, _ in faces]
#     spoof_msg = spoofing_detector(boxes, image)
#     spoofs = spoof_msg.respond_data
#     respond = {
#         "nums": len(spoofs),
#         "is_reals": [bool(is_spoof) for is_spoof, _ in spoofs],
#         "scores": [round(float(score), 4) for _, score in spoofs],
#         "boxes": boxes
#     }
#     print(f"RESPOND: {respond}")
#     return respond
