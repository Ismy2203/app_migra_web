import os
import logging

log_file_path = os.path.abspath("migration_logs.txt")
LOG_TEXT = []

def setup_logger():
    global LOG_TEXT
    logging.basicConfig(filename=log_file_path, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    LOG_TEXT = []

def log_message_streamlit(message):
    st.session_state.setdefault('logs', [])
    st.session_state['logs'].append(message)
    st.write(f"📝 {message}")
 
