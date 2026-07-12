import streamlit as st
from pathlib import Path

dir_path = Path(__file__).parent

def run() -> None:
    page = st.navigation(
        {
            "Pages": [
                st.Page(
                    dir_path / "hello.py", title="Hello", icon=":material/waving_hand:"
                ),
                st.Page(
                    dir_path / "stats_ingest.py",
                    title="Ingestion statistics",
                    icon=":material/table:",
                ),
            ]
        }
    )
    page.run()


if __name__ == "__main__":
    run()
