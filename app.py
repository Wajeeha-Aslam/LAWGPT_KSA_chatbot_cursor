# app.py

import streamlit as st
from lawgpt_utils import ask_chatbot, get_available_filters, get_filter_description

# Page configuration
st.set_page_config(
    page_title="⚖️ KSA LawGPT - Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .filter-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .chat-container {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<h1 class="main-header">⚖️ KSA LawGPT - Legal Assistant</h1>', unsafe_allow_html=True)

# Sidebar for filters
with st.sidebar:
    st.header("🔍 Search Filters")
    st.markdown("---")
    
    # Law type filter
    st.subheader("📚 Law Type Filter")
    available_filters = get_available_filters()
    
    selected_filter = st.selectbox(
        "Choose law type to filter by:",
        options=available_filters,
        format_func=lambda x: x.title(),
        help="Select a specific law type to focus your search"
    )
    
    # Show filter description
    filter_description = get_filter_description(selected_filter)
    st.info(f"**{selected_filter.title()}**: {filter_description}")
    
    st.markdown("---")
    
    # Information about the system
    st.subheader("ℹ️ About")
    st.markdown("""
    This legal assistant provides information based on:
    - **KSA Legal Documents** (PDFs)
    - **Court Cases** (60 cases)
    - **Real-time AI Analysis**
    
    Select a filter to focus on specific legal areas.
    """)

# Main chat interface
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask your legal question (based on KSA law):"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analyzing..."):
            # Get response with selected filter
            response = ask_chatbot(prompt, law_filter=selected_filter)
            st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>⚖️ Powered by KSA Legal Database | For educational purposes only</p>
    <p>Always consult with qualified legal professionals for specific legal advice</p>
</div>
""", unsafe_allow_html=True) 