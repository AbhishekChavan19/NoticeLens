"""
NoticeLens - Multilingual College Notice Understanding System
Main Streamlit Application Entry Point

Phase 1: PDF Text Extraction
Run with: streamlit run app.py
"""

import os
import logging

import streamlit as st
from dotenv import load_dotenv

from src.pdf.extractor import extract_from_pdf
from src.language.detector import detect_language
from src.classification.predictor import predict_notice_category
from src.extraction.extractor import extract_structured_information
from src.simplification.simplifier import simplify_notice

import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main application function."""

    # ---- Page Configuration ----
    st.set_page_config(
        page_title="NoticeLens - College Notice Understanding System",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- Header ----
    st.title("🔍 NoticeLens")
    st.subheader("Multilingual College Notice Understanding System")
    st.caption("PCCOE NLP Mini Project")
    st.divider()

    # ---- Sidebar ----
    with st.sidebar:
        st.header("⚙️ Settings")

        # OCR toggle
        ocr_enabled = st.toggle(
            "Enable OCR Fallback",
            value=True,
            help=(
                "When enabled, Tesseract OCR will be used for pages "
                "where normal text extraction produces insufficient content. "
                "Requires Tesseract to be installed on your system."
            ),
        )

        # Tesseract path (optional)
        tesseract_path = os.getenv("TESSERACT_PATH", "")
        if ocr_enabled:
            tesseract_path = st.text_input(
                "Tesseract Path (optional)",
                value=tesseract_path,
                help="Leave empty if Tesseract is on your system PATH.",
                placeholder=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            )

        # OCR languages
        ocr_languages = st.text_input(
            "OCR Languages",
            value="eng+mar",
            help="Tesseract language codes separated by '+'. Default: eng+mar",
        )

        # LLM Provider Configuration
        st.divider()
        st.header("🤖 LLM Settings")
        llm_provider = st.selectbox(
            "LLM Provider",
            options=["groq", "openai"],
            index=0,
            help="Groq offers a free tier. OpenAI requires API credits.",
        )

        if llm_provider == "groq":
            llm_api_key = st.text_input(
                "Groq API Key",
                value=os.getenv("GROQ_API_KEY", ""),
                type="password",
                help="Get a free key at https://console.groq.com",
            )
            llm_model = st.selectbox(
                "Groq Model",
                options=["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
                index=0,
                help="Qwen 3.8 27B recommended for multilingual accuracy.",
            )
        else:
            llm_api_key = st.text_input(
                "OpenAI API Key",
                value=os.getenv("OPENAI_API_KEY", ""),
                type="password",
                help="Required for OpenAI-based extraction.",
            )
            llm_model = st.selectbox(
                "OpenAI Model",
                options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
                index=0,
                help="OpenAI model for structured extraction.",
            )

        st.divider()
        st.header("📋 Pipeline Status")
        st.markdown(
            """
            | Phase | Status |
            |-------|--------|
            | PDF Extraction | ✅ Active |
            | Language Detection | ✅ Active |
            | Notice Classification | ✅ Active |
            | Info Extraction | ✅ Active |
            | Simplification | ✅ Active |
            """
        )

        st.divider()
        st.header("📂 Notice Categories")
        categories = [
            "Examination", "Academics", "Admission",
            "Scholarship", "Placement", "Internship",
            "Event", "General", "Other",
        ]
        for i, cat in enumerate(categories, 1):
            st.write(f"{i}. {cat}")

    # ---- Main Content ----
    st.header("📄 PDF Text Extraction")
    st.write(
        "Upload a college notice PDF to extract its text content. "
        "The system uses PyMuPDF for text-based PDFs and falls back to "
        "Tesseract OCR for scanned documents."
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a PDF notice",
        type=["pdf"],
        help="Upload a college notice in PDF format.",
    )

    if uploaded_file is not None:
        st.info(f"📎 **File:** {uploaded_file.name}  |  **Size:** {uploaded_file.size / 1024:.1f} KB")

        # Process button
        if st.button("🚀 Extract Text & Process Notice", type="primary", use_container_width=True):
            _process_pdf(uploaded_file, ocr_enabled, tesseract_path, ocr_languages, llm_api_key, llm_model, llm_provider)


def _process_pdf(uploaded_file, ocr_enabled, tesseract_path, ocr_languages, llm_api_key, llm_model, llm_provider):
    """Process the uploaded PDF and display results."""

    file_bytes = uploaded_file.read()

    with st.spinner("Extracting text from PDF..."):
        result = extract_from_pdf(
            file_bytes=file_bytes,
            ocr_enabled=ocr_enabled,
            tesseract_path=tesseract_path if tesseract_path else None,
            ocr_languages=ocr_languages,
        )

    # ---- Display Results ----

    if not result.success:
        st.error(f"❌ Extraction failed: {result.error}")
        if result.warnings:
            for w in result.warnings:
                st.warning(w)
        return

    # Run Language Detection (Phase 3)
    lang_result = detect_language(result.extracted_text)

    # Success metrics
    st.success("✅ Processing completed successfully!")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Pages", result.page_count)
    with col2:
        method_labels = {
            "text": "📝 Direct Text",
            "ocr": "🔎 OCR",
            "mixed": "📝+🔎 Mixed",
        }
        st.metric(
            "⚙️ Extractor",
            method_labels.get(result.extraction_method, result.extraction_method),
        )
    with col3:
        lang_flags = {
            "English": "🇬🇧 English",
            "Marathi": "🇮🇳 Marathi",
            "Mixed": "🌐 Mixed (En+Mr)",
            "Unknown": "❓ Unknown",
        }
        st.metric("🗣️ Language", lang_flags.get(lang_result.language, lang_result.language))
    with col4:
        st.metric("🎯 Confidence", f"{lang_result.confidence * 100:.1f}%")

    # Language distribution callout
    st.info(
        f"**Language Analysis Details:** "
        f"English Script: `{lang_result.distribution.get('en', 0)*100:.1f}%` | "
        f"Marathi (Devanagari) Script: `{lang_result.distribution.get('mr', 0)*100:.1f}%` | "
        f"Detection Engine: `{lang_result.detection_method}`"
    )

    # ---- Phase 4: Notice Classification ----
    st.divider()
    st.subheader("🏷️ Notice Classification (Phase 4)")

    try:
        clf_result = predict_notice_category(result.extracted_text, threshold=0.40)

        category_icons = {
            "Examination": "🎓 Examination",
            "Academics": "📚 Academics",
            "Admission": "📝 Admission",
            "Scholarship": "💰 Scholarship",
            "Placement": "💼 Placement",
            "Internship": "🤝 Internship",
            "Event": "🎉 Event",
            "General": "📢 General",
            "Other": "📦 Other",
            "Other/Uncertain": "❓ Other/Uncertain",
        }

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "🏷️ Predicted Category",
                category_icons.get(clf_result["category"], clf_result["category"]),
            )
        with col2:
            st.metric("🎯 Classification Confidence", f"{clf_result['confidence'] * 100:.1f}%")
        with col3:
            st.metric("🤖 Model Architecture", clf_result.get("model_used", "XLM-RoBERTa"))

        if clf_result["category"] == "Other/Uncertain":
            st.warning(
                "⚠️ Confidence score is below the configured threshold (40%). "
                "Classified as 'Other/Uncertain' to prevent false predictions."
            )

        with st.expander("📊 All Category Probabilities", expanded=False):
            prob_df = pd.DataFrame(
                list(clf_result["probabilities"].items()),
                columns=["Category", "Probability"],
            ).sort_values(by="Probability", ascending=False)
            st.dataframe(prob_df, use_container_width=True, hide_index=True)

    except Exception as e:
        clf_result = {"category": "General"}
        st.warning(f"Classification pending model training: {e}")

    # ---- Phase 5: LLM Structured Information Extraction ----
    st.divider()
    st.subheader("💡 Structured Information Extraction (Phase 5)")

    if not llm_api_key:
        st.warning(
            f"🔑 **{llm_provider.capitalize()} API Key Missing:** Please provide your API key in the sidebar."
        )
    else:
        with st.spinner(f"Extracting structured notice information using {llm_provider}/{llm_model}..."):
            ext_result = extract_structured_information(
                text=result.extracted_text,
                category=clf_result.get("category", "General"),
                language=lang_result.language,
                api_key=llm_api_key,
                model=llm_model,
                provider=llm_provider,
            )

        if not ext_result.success:
            st.error(f"❌ Extraction Error: {ext_result.error}")
        else:
            data = ext_result.data
            st.success(f"✅ Extracted structured metadata via `{ext_result.model_used}`!")

            # Overview Cards
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**📌 Notice Title:** {data.title or 'N/A'}")
                st.markdown(f"**🎯 Target Audience:** {data.target_audience or 'N/A'}")
                st.markdown(f"**⚡ Action Required:** {'Yes' if data.action_required else 'No'}")
            with col_b:
                st.markdown(f"**⏰ Deadline:** `{data.deadline or 'None'}`")
                st.markdown(f"**💰 Fees / Fines:** {data.fees or 'None'}")
                st.markdown(f"**📍 Venue:** {data.venue or 'None'}")

            st.markdown(f"**📝 What is this about?**  \n{data.what_is_this_about or 'N/A'}")

            # Specific Lists
            col_x, col_y = st.columns(2)
            with col_x:
                if data.actions:
                    st.markdown("**👉 Actions Required:**")
                    for act in data.actions:
                        st.markdown(f"- {act}")

                if data.documents_required:
                    st.markdown("**📂 Documents Required:**")
                    for doc in data.documents_required:
                        st.markdown(f"- {doc}")

            with col_y:
                if data.important_dates:
                    st.markdown("**📅 Important Dates:**")
                    for d in data.important_dates:
                        st.markdown(f"- `{d}`")

                if data.portal_or_link:
                    st.markdown(f"**🌐 Portal / Link:** {data.portal_or_link}")

                if data.contact_information:
                    st.markdown(f"**📞 Contact Info:** {data.contact_information}")

            # Full JSON View
            with st.expander("🔍 Full Extracted JSON (Schema Validated)", expanded=False):
                st.json(data.model_dump())

            # ---- Phase 6: Simplification ----
            st.divider()
            st.subheader("📖 Student-Friendly Explanation (Phase 6)")

            with st.spinner(f"Generating simplified explanation using {llm_provider}/{llm_model}..."):
                simp_result = simplify_notice(
                    extracted_data=data,
                    api_key=llm_api_key,
                    model=llm_model,
                    provider=llm_provider,
                )

            if not simp_result.success:
                st.error(f"❌ Simplification Error: {simp_result.error}")
            else:
                st.success(f"✅ Simplified explanation generated via `{simp_result.model_used}`!")

                tab_en, tab_mr = st.tabs(["🇬🇧 Simple English", "🇮🇳 सोपे मराठी"])

                with tab_en:
                    en = simp_result.simple_english
                    if en:
                        st.markdown(f"### 📌 What is this notice about?\n{en.what_is_this_notice_about}")
                        st.markdown(f"**👤 Who is it for?** {en.who_is_it_for}")
                        st.markdown(f"**✅ What do I need to do?** {en.what_do_i_need_to_do}")
                        if en.deadline:
                            st.markdown(f"**⏰ Deadline:** `{en.deadline}`")
                        if en.important_dates:
                            st.markdown(f"**📅 Important Dates:** {en.important_dates}")
                        if en.documents_required:
                            st.markdown(f"**📂 Documents Required:** {en.documents_required}")
                        if en.fees:
                            st.markdown(f"**💰 Fees:** {en.fees}")
                        if en.eligibility:
                            st.markdown(f"**🎯 Eligibility:** {en.eligibility}")
                        if en.important_note:
                            st.info(f"💡 **Important Note:** {en.important_note}")
                    else:
                        st.warning("English simplification data not available.")

                with tab_mr:
                    mr = simp_result.simple_marathi
                    if mr:
                        st.markdown(f"### 📌 हा नोटीस कशाबद्दल आहे?\n{mr.notice_about}")
                        st.markdown(f"**👤 कोणासाठी आहे?** {mr.who_is_it_for}")
                        st.markdown(f"**✅ मला काय करावे लागेल?** {mr.what_to_do}")
                        if mr.deadline:
                            st.markdown(f"**⏰ अंतिम तारीख:** `{mr.deadline}`")
                        if mr.important_dates:
                            st.markdown(f"**📅 महत्त्वाच्या तारखा:** {mr.important_dates}")
                        if mr.documents_required:
                            st.markdown(f"**📂 आवश्यक कागदपत्रे:** {mr.documents_required}")
                        if mr.fees:
                            st.markdown(f"**💰 फी:** {mr.fees}")
                        if mr.eligibility:
                            st.markdown(f"**🎯 पात्रता:** {mr.eligibility}")
                        if mr.important_note:
                            st.info(f"💡 **महत्त्वाची सूचना:** {mr.important_note}")
                    else:
                        st.warning("Marathi simplification data not available.")

    # Warnings
    if result.warnings:
        with st.expander(f"⚠️ Warnings ({len(result.warnings)})", expanded=False):
            for w in result.warnings:
                st.warning(w)

    st.divider()

    # ---- Full Extracted Text ----
    st.subheader("📝 Full Extracted Text")
    st.text_area(
        "Complete extracted content",
        value=result.extracted_text,
        height=400,
        disabled=True,
        label_visibility="collapsed",
    )

    # ---- Per-Page Breakdown ----
    st.subheader("📑 Per-Page Breakdown")

    for page_result in result.per_page:
        method_icon = {
            "text": "📝",
            "ocr": "🔎",
            "empty": "⚠️",
        }.get(page_result.method, "❓")

        with st.expander(
            f"Page {page_result.page_number}  "
            f"{method_icon} {page_result.method.upper()}  |  "
            f"{page_result.char_count} chars"
        ):
            if page_result.text.strip():
                st.text_area(
                    f"Page {page_result.page_number} text",
                    value=page_result.text,
                    height=250,
                    disabled=True,
                    key=f"page_{page_result.page_number}",
                    label_visibility="collapsed",
                )
            else:
                st.warning("No usable text extracted from this page.")


if __name__ == "__main__":
    main()
