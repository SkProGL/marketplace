import torch
import json
import numpy as np
from .brfn_train import FactorizationMachine
from safetensors.torch import load_file


class RecommenderService:

    def __init__(self, model_path, user_map_path, item_map_path, product_map_path, field_dims):

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = FactorizationMachine(field_dims, embed_dim=32).to(self.device)
        self.model.load_state_dict(load_file(model_path))
        self.model.eval()

        with open(user_map_path) as f:
            self.user_map = json.load(f)

        with open(item_map_path) as f:
            self.item_map = json.load(f)

        with open(product_map_path) as f:
            self.product_map = json.load(f)

        # reverse map (important for output)
        self.rev_item_map = {v: k for k, v in self.item_map.items()}

    def recommend(self, user_id, top_k=3):

        if str(user_id) not in self.user_map:
            return []

        u_idx = self.user_map[str(user_id)]
        num_items = len(self.item_map)

        users = torch.full((num_items,), u_idx, dtype=torch.long)
        items = torch.arange(num_items, dtype=torch.long)

        x = torch.stack([users, items], dim=1).to(self.device)

        with torch.no_grad():
            scores = self.model(x).cpu().numpy()

        top_idx = np.argsort(scores)[-top_k:][::-1]

        results = []

        for idx in top_idx:
            original_item_id = str(self.rev_item_map[int(idx)])
            product_name = self.product_map.get(original_item_id, "Unknown Product")

            results.append({
                "name": product_name,
                "score": float(scores[idx]),
            })

        return results