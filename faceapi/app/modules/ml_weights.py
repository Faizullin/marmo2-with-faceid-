import logging

from app.modules.antispoof.library.task_manager import (FaceDetectorWorker,
                                                        SpoofingDetectorWorker)
from app.modules.storage import storage

logger = logging.getLogger(__name__)


weights_path = storage.get_model_weights_dir_path()
antispoofing_model_path = weights_path.joinpath("fasnet_v1se_v2.pth.tar")
retina_face_detector_model_path = weights_path.joinpath(
    "retina_face.pth.tar")
face_detector = FaceDetectorWorker(
    model_path=retina_face_detector_model_path,
    detect_threshold=0.95,
    scale_size=720,
    device="cpu"
)
spoofing_detector = SpoofingDetectorWorker(
    model_path=antispoofing_model_path,
    device="cpu"
)


async def load_models():
    logger.info("load_models: start")
    logger.info("load_models: end")
