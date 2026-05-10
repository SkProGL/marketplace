import os
from .inference import RecommenderService


MODEL_DIR = "recommender_results"

_service = None  # singleton


def get_recommender():

    global _service

    if _service is None:

        _service = RecommenderService(
            model_path=os.path.join(MODEL_DIR, "F1.safetensors"),
            user_map_path=os.path.join(MODEL_DIR, "user_map.json"),
            item_map_path=os.path.join(MODEL_DIR, "item_map.json"),
            product_map_path=os.path.join(MODEL_DIR, "product_name_map.json"),
            field_dims=[1000, 1000]  # ideally load dynamically later
        )

    return _service