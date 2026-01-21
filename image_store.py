import os
from tqdm import tqdm
from typing import Iterator
from embeddings import ImageData, embed_img, load_imgs

from pyobvector import (
    VECTOR,
    ObVecClient,
)

from sqlalchemy import Column, Integer, JSON, String
from sqlalchemy import func

cols = [
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("file_name", String(512)),
    Column("file_path", String(2048)),
    Column("caption", String(2048)),
    Column("embedding", VECTOR(512)),
]

output_fields = [
    "id",
    "file_name",
    "file_path",
    "caption",
    # "embedding",
]


class OBImageStore:
    def __init__(
        self,
        *,
        user: str = "",
        uri: str = "",
        db_name: str = "",
        password: str = "",
        table_name: str = "image_store",
        **kwargs,
    ):
        self.table_name = table_name
        self.client = ObVecClient(
            user=user,
            uri=uri,
            db_name=db_name,
            password=password,
        )

    def load_image_dir(self, dir_path: str, batch_size: int = 32) -> Iterator:
        if not self.client.check_table_exists(self.table_name):
            self.client.create_table(self.table_name, columns=cols)
            vals = []
            params = self.client.perform_raw_text_sql(
                "SHOW PARAMETERS LIKE '%ob_vector_memory_limit_percentage%'"
            )
            for row in params:
                val = int(row[6])
                vals.append(val)
            if len(vals) == 0:
                print("ob_vector_memory_limit_percentage not found in parameters.")
                exit(1)
            if any(val == 0 for val in vals):
                try:
                    self.client.perform_raw_text_sql(
                        "ALTER SYSTEM SET ob_vector_memory_limit_percentage = 30"
                    )
                except Exception as e:
                    raise Exception(
                        "Failed to set ob_vector_memory_limit_percentage to 30.", e
                )
            self.client.perform_raw_text_sql("SET ob_query_timeout=100000000")
            self.client.create_index(
                self.table_name,
                is_vec_index=True,
                index_name="img_embedding_idx",
                column_names=["embedding"],
                vidx_params="distance=l2, type=hnsw, lib=vsag",
            )
            # Create fulltext index for caption
            self.client.perform_raw_text_sql(
                f"ALTER TABLE {self.table_name} ADD FULLTEXT INDEX caption_idx (caption)"
            )
        batch = []
        total = 0
        for _, _, files in os.walk(dir_path):
            total += len(files)
        for img in tqdm(load_imgs(dir_path), total=total):
            batch.append(img.model_dump())
            yield
            if len(batch) == batch_size:
                self.client.insert(self.table_name, batch)
                batch = []
        if len(batch) > 0:
            self.client.insert(self.table_name, batch)

    def search(self, image_path: str, limit: int = 10) -> list[dict[str, any]]:
        target_embedding = embed_img(image_path)

        res = self.client.ann_search(
            self.table_name,
            vec_data=target_embedding,
            vec_column_name="embedding",
            topk=limit,
            distance_func=func.l2_distance,
            output_column_names=output_fields,
            with_dist=True,
        )
        return [
            {
                "id": r[0],
                "file_name": r[1],
                "file_path": r[2],
                "caption": r[3],
                "distance": r[4],
            }
            for r in res
        ]

    def text_search(self, query_text: str, limit: int = 50) -> list[dict[str, any]]:
        """Full-text search based on caption"""
        # Escape single quotes in query text
        escaped_query = query_text.replace("'", "''")
        sql = f"""
            SELECT id, file_name, file_path, caption,
                   MATCH(caption) AGAINST('{escaped_query}' IN NATURAL LANGUAGE MODE) as text_score
            FROM {self.table_name}
            WHERE MATCH(caption) AGAINST('{escaped_query}' IN NATURAL LANGUAGE MODE)
            ORDER BY text_score DESC
            LIMIT {limit}
        """
        results = self.client.perform_raw_text_sql(sql)
        return [
            {
                "id": r[0],
                "file_name": r[1],
                "file_path": r[2],
                "caption": r[3],
                "text_score": float(r[4]),
            }
            for r in results
        ]

    def _fuse_results(
        self, vector_results: list, text_results: list, vector_weight: float, limit: int
    ) -> list[dict[str, any]]:
        """Normalize scores and fuse results with weighted sum"""
        # Normalize vector distances to similarities [0, 1]
        vec_dict = {r["id"]: r["distance"] for r in vector_results}
        if vec_dict:
            max_dist = max(vec_dict.values()) or 1.0
            vec_norm = {img_id: 1 - (d / max_dist) for img_id, d in vec_dict.items()}
        else:
            vec_norm = {}

        # Normalize text scores to [0, 1]
        txt_dict = {r["id"]: r["text_score"] for r in text_results}
        if txt_dict:
            max_score = max(txt_dict.values()) or 1.0
            txt_norm = {img_id: s / max_score for img_id, s in txt_dict.items()}
        else:
            txt_norm = {}

        # Weighted fusion
        final_scores = {}
        all_ids = set(vec_norm.keys()) | set(txt_norm.keys())
        text_weight = 1 - vector_weight

        for img_id in all_ids:
            vec_sim = vec_norm.get(img_id, 0)
            txt_sim = txt_norm.get(img_id, 0)
            final_scores[img_id] = vector_weight * vec_sim + text_weight * txt_sim

        # Sort by fusion score
        sorted_ids = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[
            :limit
        ]

        # Build full result with complete info
        id_to_info = {}
        for r in vector_results + text_results:
            if r["id"] not in id_to_info:
                id_to_info[r["id"]] = r

        return [
            {**id_to_info[img_id], "fusion_score": score, "distance": id_to_info[img_id].get("distance")}
            for img_id, score in sorted_ids
            if img_id in id_to_info
        ]

    def hybrid_search(
        self, image_path: str, limit: int = 10, vector_weight: float = 0.7, distance_threshold: float = None
    ) -> list[dict[str, any]]:
        """Hybrid search: vector + text with weighted fusion"""
        # Pure vector search
        if vector_weight == 1.0:
            results = self.search(image_path, limit=limit)
            # Apply distance threshold filter
            if distance_threshold is not None:
                results = [r for r in results if r.get("distance", 0) <= distance_threshold]
            return results

        # Pure text search
        if vector_weight == 0.0:
            from embeddings import caption_img

            query_caption = caption_img(image_path)
            results = self.text_search(query_caption, limit=limit)
            # Add distance field as None for consistency
            for r in results:
                r["distance"] = None
            return results

        # Hybrid: recall 5x, then fuse
        recall_limit = limit * 5
        vector_results = self.search(image_path, limit=recall_limit)
        
        # Filter vector results by distance threshold before fusion
        if distance_threshold is not None:
            vector_results = [r for r in vector_results if r.get("distance", 0) <= distance_threshold]

        from embeddings import caption_img

        query_caption = caption_img(image_path)
        text_results = self.text_search(query_caption, limit=recall_limit)

        return self._fuse_results(vector_results, text_results, vector_weight, limit)
