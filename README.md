English | [中文版](./README_zh.md) | [日本語版](./README_ja.md)

# Image Search Application

## Introduction

Leveraging OceanBase's vector storage and retrieval capabilities, we can build an image search application. This application embeds images as vectors and stores them in the database, while automatically generating textual descriptions for images. It supports three modes: vector search, full-text search, and hybrid search. Users can upload images, and the application will search and return the most similar images from the database.

**Key Features**:
- **Vector Search**: Similarity search based on image visual features
- **Automatic Description Generation**: Automatically generate image text descriptions using APIs (e.g., Qwen-VL)
- **Hybrid Search**: Combine vector search and full-text search to improve accuracy
- **Adjustable Weights**: Support adjusting the weight ratio between vector and text (0.0-1.0)
- **Distance Threshold Filtering**: Set distance threshold to filter search results

Note: You need to prepare some images and update the `Image Base` configuration in the UI. If you don't have local images, you can download datasets online, such as the [Animals-10](https://www.kaggle.com/datasets/alessiocorrado99/animals10/data) dataset on Kaggle.

## Prerequisites

1. Install [Python 3.9](https://www.python.org/downloads/) or above and the corresponding [Pip](https://pip.pypa.io/en/stable/installation/) tool

2. Install [Docker](https://docs.docker.com/get-docker/) to start the seekdb database container

3. Install [uv](https://github.com/astral-sh/uv) as the dependency management tool, refer to the command below

```bash
python3 -m pip install uv
```

4. Obtain seekdb database connection information

## Setup Steps

### 1. Deploy seekdb

Start a seekdb docker container with the following command:

```bash
docker run -d -p 2881:2881 -p 2886:2886 --name seekdb oceanbase/seekdb
```

If you need data persistence, you can mount a data directory:

```bash
# Linux or MacOS
mkdir -p seekdb
docker run -d -p 2881:2881 -p 2886:2886 \
  -v $PWD/seekdb:/var/lib/oceanbase \
  --name seekdb oceanbase/seekdb

# Windows
docker volume create seekdb
docker run -d -p 2881:2881 -p 2886:2886 \
  -v seekdb:/var/lib/oceanbase \
  --name seekdb oceanbase/seekdb
```

For more information on seekdb configuration and usage, please refer to the [seekdb official repository](https://github.com/oceanbase/seekdb).

### 2. Install Dependencies

```bash
uv sync
```

### 3. Configure Environment Variables

We provide a `.env.example` file. You need to copy it to `.env` and fill in your database connection information and API configuration. Refer to the commands below:

```bash
cp .env.example .env
vi .env
```

**Required Configuration**:
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Database connection information
- `API_KEY`: API key for image description generation (e.g., Qwen DashScope API Key)
- `BASE_URL`: API address (default: `https://dashscope.aliyuncs.com/compatible-mode/v1`)
- `MODEL`: Model name (default: `qwen-vl-max`)

### 4. Start Image Search UI

```bash
uv run streamlit run --server.runOnSave false image_search_ui.py
```

### 5. Process and Store Image Data

After opening the application interface, you can see the "Image Base" input box in the left sidebar. Fill in the absolute path of your prepared image directory, then click the "Load Images" button. The application will process and store the image data, and you will see the image processing progress on the interface.

### 6. Use Image Search

After the images are processed, you will see an image upload section at the top of the interface. You can upload an image to search for similar images. The application will search and return the most similar images from the database.

#### Search Parameters

- **Recall Number**: Number of similar images to return (1-30, default 10)
- **Vector Weight**: Controls the search mode
  - `1.0`: Pure vector search (based on image visual features only)
  - `0.7` (recommended): Hybrid search, vector-dominant with text supplement
  - `0.5`: Equal weight for vector and text
  - `0.0`: Pure text search (based on image description matching only)
- **Distance Threshold**: Only display results with vector distance less than or equal to this value (default 0.6, only applies to vector search)

#### Search Results

Each search result will display:
- Similar image
- Image description
- Similarity distance (smaller distance means more similar, only shown in vector search)
- File path

![image_search_ui](./demo/image-search-demo.png)

## FAQ

### 1. How to obtain an image description API Key?

This application requires a vision model API that supports OpenAI-compatible interfaces to generate image descriptions. We recommend using **Qwen-VL**:

1. Visit [Alibaba Cloud DashScope](https://dashscope.aliyun.com/)
2. Enable Qwen service
3. Create an API Key
4. Configure `API_KEY` in the `.env` file

You can also use other services that support OpenAI-compatible interfaces (such as GPT-4V, Azure OpenAI, etc.), and modify the `BASE_URL` and `MODEL` configuration accordingly.

### 2. What to do if libGL.so.1 file is not found?

If you encounter `ImportError: libGL.so.1: cannot open shared object file` when running the application UI, you can refer to [this post](https://stackoverflow.com/questions/55313610/importerror-libgl-so-1-cannot-open-shared-object-file-no-such-file-or-directo) for a solution.

On CentOS, run the following command:

```bash
sudo yum install mesa-libGL -y
```

On Ubuntu/Debian, run the following command:

```bash
sudo apt-get install libgl1
```

### 3. How to choose the right vector weight?

Choose the appropriate vector weight based on your search needs:

- **0.9-1.0**: Visual similarity is most important (e.g., finding images with similar composition, color, and style)
- **0.6-0.8**: Visual-dominant with semantic supplement (recommended, best balance)
- **0.3-0.5**: Equal importance for visual and semantic
- **0.0-0.2**: Semantic most important (e.g., "find all foxes", regardless of visual differences)

### 4. What to do if pkg_resources module is not found?

If you encounter `ModuleNotFoundError: No module named 'pkg_resources'` when running the application UI, you can refer to [this post](https://stackoverflow.com/questions/7446187/no-module-named-pkg-resources) for a solution.

Specifically, refer to the following commands:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install setuptools
```
