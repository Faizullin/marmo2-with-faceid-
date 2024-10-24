import asyncio
import logging
from typing import Dict
from deepface.modules import modeling

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def _start_async_load(args: Dict):
    modeling.build_model(**args)


async def load_models():
    # cwd = os.getcwd()
    # weights_path = os.path.join(cwd, ".deepface")
    # weights_path = os.path.join(weights_path, "weights")
    # if not os.path.exists(weights_path):
    #     os.makedirs(weights_path)
    models = [
        {
            "task": "facial_recognition",
            "model_name": "VGG-Face",
        }
    ]
    logger.info("load_models: start")
    tasks = [_start_async_load(i) for i in models]
    await asyncio.gather(*tasks)
    logger.info("load_models: end")
