import os
import time
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from torch.utils.data import DataLoader, TensorDataset
from dataclasses import dataclass
from safetensors.torch import save_file

from .. import run_utils
from .config import RecommenderMetrics


@dataclass
class FMConfig:
    run: str = "F1"
    embed_dim: int = 32
    learning_rate: float = 0.001
    batch_size: int = 2048
    epochs: int = 10
    sample_frac: float = 1.0
    model_type: str = "marketplace_fm"


class FactorizationMachine(nn.Module):

    def __init__(self, field_dims, embed_dim):
        super().__init__()

        self.offsets = np.array(
            (0, *np.cumsum(field_dims)[:-1])
        )

        self.linear = nn.Embedding(
            sum(field_dims),
            1
        )

        self.embedding = nn.Embedding(
            sum(field_dims),
            embed_dim
        )

        self.bias = nn.Parameter(
            torch.zeros(1)
        )

        nn.init.xavier_uniform_(
            self.embedding.weight
        )

    def forward(self, x):

        x = x + x.new_tensor(
            self.offsets
        ).unsqueeze(0)

        linear = (
            torch.sum(self.linear(x), dim=1)
            + self.bias
        )

        emb = self.embedding(x)

        square_of_sum = torch.sum(
            emb,
            dim=1
        ) ** 2

        sum_of_square = torch.sum(
            emb ** 2,
            dim=1
        )

        interaction = 0.5 * torch.sum(
            square_of_sum - sum_of_square,
            dim=1,
            keepdim=True
        )

        return torch.sigmoid(
            linear + interaction
        ).squeeze()

def build_interactions(users_df, products_df, orders_df):
    interactions = []

    # map product row index -> actual product
    products_df = products_df.reset_index(drop=True)
    products_df["product_id"] = products_df.index + 1

    valid_users = set(users_df["id"].astype(int).tolist())
    valid_products = set(products_df["product_id"].astype(int).tolist())

    for _, order in orders_df.iterrows():

        # skip malformed rows
        if pd.isna(order.get("product_ids")):
            continue

        raw_products = str(order["product_ids"])

        # convert:
        # "37,74,7"
        # into [37,74,7]
        product_list = []

        for p in raw_products.split(","):
            p = p.strip().replace('"', "")

            if not p:
                continue

            try:
                product_id = int(float(p))

                if product_id in valid_products:
                    product_list.append(product_id)

            except:
                continue

        if len(product_list) == 0:
            continue

        # generate fake user if dataset has no customer_id
        user_id = np.random.choice(list(valid_users))

        for product_id in product_list:
            interactions.append({
                "user_id": user_id,
                "product_id": product_id,
                "is_reorder": 1
            })

    interactions_df = pd.DataFrame(interactions)

    print(f"Interactions loaded: {len(interactions_df)}")

    return interactions_df

def load_data(
    orders_path='task_1/data/orders.csv',
    products_path='task_1/data/products.csv',
    users_path='task_1/data/users.csv',
    sample_frac=1.0
):

    print("\n--- Loading marketplace datasets ---")

    users_df = pd.read_csv(users_path, encoding="utf-8-sig")
    products_df = pd.read_csv(products_path, encoding="utf-8-sig")
    orders_df = pd.read_csv(orders_path, encoding="utf-8-sig")

    users_df.columns = users_df.columns.str.strip()
    products_df.columns = products_df.columns.str.strip()
    orders_df.columns = orders_df.columns.str.strip()

    products_df = products_df.reset_index(drop=True)
    products_df["product_id"] = products_df.index + 1

    print(products_df.columns.tolist())

    print(users_df.columns.tolist())
    # =========================
    # FILTER CUSTOMERS
    # =========================

    customer_df = users_df[
        users_df['category']
        .str.lower() == 'customer'
    ].copy()

    valid_customer_ids = set(
        customer_df['id']
    )

    # =========================
    # BUILD INTERACTIONS
    # =========================

    df = build_interactions(users_df, products_df, orders_df)

    # =========================
    # OPTIONAL SAMPLE
    # =========================

    if sample_frac < 1.0:
        df = df.sample(
            frac=sample_frac,
            random_state=42
        )

    # =========================
    # ENCODE USERS/ITEMS
    # =========================

    user_ids = sorted(
        df['user_id'].unique()
    )

    product_ids = sorted(
        df['product_id'].unique()
    )

    user_map = {
        uid: idx
        for idx, uid in enumerate(user_ids)
    }

    item_map = {
        pid: idx
        for idx, pid in enumerate(product_ids)
    }

    df['user_id'] = df['user_id'].map(
        user_map
    )

    df['product_id'] = df['product_id'].map(
        item_map
    )

    # =========================
    # PRODUCT NAMES
    # =========================

    product_name_map = (
        products_df[['product_id', 'name']]
        .drop_duplicates()
        .set_index('product_id')['name']
        .to_dict()
    )

    # =========================
    # SHUFFLE + SPLIT
    # =========================

    df = df.sample(
        frac=1,
        random_state=42
    )

    split_idx = int(
        len(df) * 0.8
    )

    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    val_split = int(
        len(train_df) * 0.9
    )

    val_df = train_df.iloc[val_split:]
    train_df = train_df.iloc[:val_split]

    # =========================
    # FEATURES
    # =========================

    cat_features = [
        'user_id',
        'product_id'
    ]

    X_train = train_df[
        cat_features
    ].values

    y_train = train_df[
        'is_reorder'
    ].values

    X_val = val_df[
        cat_features
    ].values

    y_val = val_df[
        'is_reorder'
    ].values

    X_test = test_df[
        cat_features
    ].values

    y_test = test_df[
        'is_reorder'
    ].values

    field_dims = [
        len(user_map),
        len(item_map)
    ]

    print(f"Users: {len(user_map)}")
    print(f"Products: {len(item_map)}")

    return (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
        field_dims,
        len(user_map),
        len(item_map),
        test_df,
        user_map,
        item_map,
        product_name_map,
        train_df
    )


def calculate_precision_recall_at_k(
    model,
    u_test,
    i_test,
    y_test,
    num_items,
    device,
    k=10
):

    model.eval()

    user_test_data = pd.DataFrame({
        'user_id': u_test,
        'product_id': i_test,
        'is_reorder': y_test
    })

    positive_users = user_test_data[
        user_test_data['is_reorder'] == 1
    ]['user_id'].unique()

    if len(positive_users) == 0:
        return 0.0, 0.0

    precisions = []
    recalls = []

    sampled_users = np.random.choice(
        positive_users,
        min(100, len(positive_users)),
        replace=False
    )

    for u_idx in sampled_users:

        actual_relevant = set(
            user_test_data[
                (user_test_data['user_id'] == u_idx)
                &
                (user_test_data['is_reorder'] == 1)
            ]['product_id'].values
        )

        x_vec = torch.stack([
            torch.full(
                (num_items,),
                u_idx,
                dtype=torch.long
            ),
            torch.arange(
                num_items,
                dtype=torch.long
            )
        ], dim=1).to(device)

        with torch.no_grad():
            scores = model(
                x_vec
            ).cpu().numpy()

        top_k_idx = np.argsort(
            scores
        )[-k:][::-1]

        top_k_items = set(top_k_idx)

        hits = len(
            actual_relevant.intersection(
                top_k_items
            )
        )

        precisions.append(hits / k)
        recalls.append(
            hits / len(actual_relevant)
        )

    return (
        np.mean(precisions),
        np.mean(recalls)
    )


def train_fm(
    run_id="F1",
    output_dir="recommender_results"
):

    config = FMConfig(run=run_id)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
        field_dims,
        num_users,
        num_items,
        test_df,
        user_map,
        item_map,
        product_name_map,
        train_df

    ) = load_data(
        sample_frac=config.sample_frac
    )

    train_loader = DataLoader(
        TensorDataset(
            torch.tensor(
                X_train,
                dtype=torch.long
            ),
            torch.tensor(
                y_train,
                dtype=torch.float32
            )
        ),
        batch_size=config.batch_size,
        shuffle=True
    )

    val_loader = DataLoader(
        TensorDataset(
            torch.tensor(
                X_val,
                dtype=torch.long
            ),
            torch.tensor(
                y_val,
                dtype=torch.float32
            )
        ),
        batch_size=config.batch_size,
        shuffle=False
    )

    model = FactorizationMachine(
        field_dims,
        config.embed_dim
    ).to(device)

    optimizer = optim.Adam(
        model.parameters(),
        lr=config.learning_rate
    )

    criterion = nn.BCELoss()

    metrics = RecommenderMetrics(
        run=f"{config.run}_metrics"
    )

    start_time = time.time()

    print(f"\n--- Training FM Run {config.run} ---")

    for epoch in range(config.epochs):

        model.train()

        total_loss = 0

        for Xb, yb in train_loader:

            Xb = Xb.to(device)
            yb = yb.to(device)

            optimizer.zero_grad()

            preds = model(Xb)

            loss = criterion(
                preds,
                yb
            )

            loss.backward()

            optimizer.step()

            total_loss += loss.item()

        # =========================
        # VALIDATION
        # =========================

        model.eval()

        val_acc = 0
        total_test = 0

        with torch.no_grad():

            for Xb, yb in val_loader:

                Xb = Xb.to(device)
                yb = yb.to(device)

                preds = model(Xb)

                val_acc += (
                    (preds > 0.5) == yb
                ).sum().item()

                total_test += yb.size(0)

        final_val_acc = (
            val_acc / total_test
        )

        avg_train_loss = (
            total_loss / len(train_loader)
        )

        metrics.epochs.append(
            epoch + 1
        )

        metrics.train_loss.append(
            avg_train_loss
        )

        metrics.test_accuracy.append(
            final_val_acc
        )

        print(
            f"Epoch {epoch+1} | "
            f"Loss: {avg_train_loss:.4f} | "
            f"Val Acc: {final_val_acc:.4f}"
        )

    metrics.elapsed_time_min = (
        time.time() - start_time
    ) / 60

    metrics.final_accuracy = (
        metrics.test_accuracy[-1]
    )

    # =========================
    # SAVE MODEL
    # =========================

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    save_file(
        model.state_dict(),
        os.path.join(
            output_dir,
            f'{config.run}.safetensors'
        )
    )

# =========================
# SAVE ENCODERS + PRODUCT MAP
# =========================

    with open(os.path.join(output_dir, "user_map.json"), "w") as f:
        json.dump({int(k): int(v) for k, v in user_map.items()}, f)

    with open(os.path.join(output_dir, "item_map.json"), "w") as f:
        json.dump({int(k): int(v) for k, v in item_map.items()}, f)

    with open(os.path.join(output_dir, "product_name_map.json"), "w") as f:
        json.dump(product_name_map, f)

    print("\n--- Calculating Precision@K ---")

    u_test = X_test[:, 0]
    i_test = X_test[:, 1]

    p_at_k, r_at_k = calculate_precision_recall_at_k(
        model,
        u_test,
        i_test,
        y_test,
        num_items,
        device,
        k=10
    )

    metrics.precision_at_k = p_at_k
    metrics.recall_at_k = r_at_k

    print(
        f"Precision@10: {p_at_k:.4f}"
    )

    print(
        f"Recall@10: {r_at_k:.4f}"
    )

    run_utils.save_run_data(
        config,
        metrics,
        output_dir
    )

    print(
        f"\nFM training complete: {config.run}"
    )


if __name__ == "__main__":
    train_fm("F1")