import os
import time
import dotenv

dotenv.load_dotenv()

import streamlit as st
from image_store import OBImageStore
from connection import connection_args
from i18n import t
from embeddings import caption_img

table_name = os.getenv("IMG_TABLE_NAME", "image_search")
tmp_path = "tmp/temp.jpg"


st.set_page_config(
    layout="wide",
    page_title=t("title"),
    page_icon="demo/ob-icon.png",
)
st.title(t("title"))
st.caption(t("caption"))

with st.sidebar:
    st.title(t("settings"))
    st.logo("demo/logo.png")
    st.subheader(t("search_setting"))
    table_name = st.text_input(
        t("table_name_input"),
        table_name,
        help=t("table_name_help"),
    )
    top_k = st.slider(t("recall_number"), 1, 30, 10, help=t("recall_number_help"))
    vector_weight = st.slider(
        t("vector_weight"),
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help=t("vector_weight_help"),
    )
    distance_threshold = st.number_input(
        t("distance_threshold"),
        min_value=0.0,
        value=0.6,
        step=0.01,
        help=t("distance_threshold_help"),
    )
    show_distance = st.checkbox(t("show_distance"), value=True)
    show_file_path = st.checkbox(t("show_file_path"), value=True)

    st.subheader(t("load_setting"))
    image_base = st.text_input(
        t("image_base_input"),
        os.getenv("IMG_BASE", None),
        help=t("image_base_help"),
        placeholder=t("image_base_placeholder"),
    )
    click_load = st.button(t("load_images"))


store = OBImageStore(
    uri=f"{connection_args['host']}:{connection_args['port']}",
    **connection_args,
    table_name=table_name,
)

table_exist = store.client.check_table_exists(table_name)
if not table_name or table_name.isspace():
    st.error(t("set_table_name_pls"))
    st.stop()
elif click_load:
    if image_base is None:
        st.error(t("set_image_base_pls"))
    elif not os.path.exists(image_base):
        st.error(t("image_base_not_exist", image_base))
    else:
        total = 0
        for _, _, files in os.walk(image_base):
            total += len(files)
        finished = 0
        bar = st.progress(0, text=t("images_loading"))
        for _ in store.load_image_dir(image_base):
            finished += 1
            bar.progress(
                finished / total, text=t("images_loading_progress", finished, total)
            )
        st.toast(t("images_loaded"), icon="🎉")
        st.balloons()
        time.sleep(2)

        st.rerun()
elif table_exist:
    uploaded_file = st.file_uploader(
        label=t("image_upload_label"),
        type=["jpg", "jpeg", "png"],
        help=t("image_upload_help"),
    )
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        col1.subheader(t("uploaded_image_header"))
        col1.caption(t("uploaded_image_caption"))

        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.read())
        
        # Generate caption
        caption = caption_img(tmp_path)
        col1.write(f"{t('image_caption')} {caption}")
        col1.image(uploaded_file, use_column_width=True)

        col2.subheader(t("similar_images_header"))
        results = store.hybrid_search(
            tmp_path, 
            limit=top_k, 
            vector_weight=vector_weight,
            distance_threshold=distance_threshold
        )
        with col2:
            if len(results) == 0:
                st.warning(t("no_similar_images"))
            else:
                tabs = st.tabs([t("image_no", i + 1) for i in range(len(results))])
                for res, tab in zip(results, tabs):
                    with tab:
                        if show_distance and res.get("distance") is not None:
                            st.write(t("distance"), f"{res['distance']:.8f}")
                        if show_file_path:
                            st.write(t("file_path"), os.path.join(res["file_path"]))
                        st.write(t("image_caption"), res.get("caption", ""))
                        st.image(res["file_path"])
else:
    st.warning(t("table_not_exist", table_name))
