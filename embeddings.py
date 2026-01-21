import os
import base64
from typing import Iterator
from towhee import AutoPipes
from pydantic import BaseModel
from openai import OpenAI


class ImageData(BaseModel):
    file_name: str = ""
    file_path: str = ""
    caption: str = ""
    embedding: list[float]


img_pipe = AutoPipes.pipeline("text_image_embedding")


def embed_img(path) -> list[float]:
    return img_pipe(path).get()[0]


def caption_img(path: str) -> str:
    """Generate image caption using OpenAI-compatible API (Qwen/OpenAI/Azure etc)"""
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("MODEL", "qwen-vl-max")
    
    if not api_key:
        return "[Error: API_KEY not set]"
    
    try:
        with open(path, "rb") as f:
            b64_image = base64.b64encode(f.read()).decode("utf-8")
        
        # Initialize client with minimal params to avoid conflicts
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is the main object in this image? Answer in 2-3 words only."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error: {str(e)}]"


def load_imgs(dir_path: str) -> Iterator[ImageData]:
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.startswith("."):
                continue
            file_path = os.path.abspath(os.path.join(root, f))
            embedding = embed_img(file_path)
            caption = caption_img(file_path)
            yield ImageData(
                file_name=f,
                file_path=file_path,
                caption=caption,
                embedding=embedding,
            )
