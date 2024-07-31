import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import re
import time
from anthropic import Anthropic

# Initialize Anthropic client
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Validating API KEY
def is_valid_api_key(api_key):
    # Attempt to make a simple API call
    try:
        client = anthropic.Anthropic(api_key=api_key)
        # Attempt to make a simple API call
        client.completions.create(
            model="claude-2.1",
            max_tokens_to_sample=1,
            prompt="This is a test."
        )
        return True
    except Exception:
        return False

        
# API Call with user prompt
def check_grammar(text):
    claude_prompt = st.secrets.get("claude_gp_prompt")
    user_message = f"""{claude_prompt} Text to check: {text}""" 

    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=3025,
        messages=[{"role": "user", "content": user_message}]
    )
    
    return response.content[0].text

# Functions for color-coding errors in entered text
def underline_text(text, parts_and_errors):
    color_map = {
        "Rechtschreibung": "green",
        "Zeichensetzung": "yellow",
        "Wortwahl": "orange",
	    "Wortstellung": "orange"
        }
    
    # Sort parts_and_errors by part length (longest first) to handle overlapping underlines
    parts_and_errors.sort(key=lambda x: len(x[0]), reverse=True)
    
    for part, error_types in parts_and_errors:
        pattern = re.escape(part)
        underline_styles = []
        for i, error_type in enumerate(error_types):
            color = color_map.get(error_type, "blue")
            offset = 6 + i * 3  # Increase offset for each additional underline
            underline_styles.append(f"text-decoration: underline; text-decoration-color: {color}; text-underline-offset: {offset}px;")
        
        style = " ".join(underline_styles)
        replacement = f'<span style="{style}">{part}</span>'
        text = re.sub(pattern, replacement, text)
    
    return text

# changed "process_csv(file_path):" to "process_df(df_):
def process_df(df_):
    sentences = {}
    index_list = df_.index.to_list()
    for i in index_list:
        sentence = df_.loc[i, "Satz"]
        part = df_.loc[i, "Satzteil"]
        error_type = df_.loc[i, "Fehler"]
            
        if sentence:
            if sentence not in sentences:
                sentences[sentence] = {}
            if part and error_type:
                if part not in sentences[sentence]:
                    sentences[sentence][part] = set()
                sentences[sentence][part].add(error_type)
    
    formatted_sentences = []
    for sentence, parts in sentences.items():
        parts_and_errors = [(part, list(error_types)) for part, error_types in parts.items()]
        formatted_sentence = underline_text(sentence, parts_and_errors)
        formatted_sentences.append(formatted_sentence)
    
    return " ".join(formatted_sentences)


# Page configuration
st.set_page_config(layout="centered", page_title="Grammar Pointer", page_icon="✅")

# Logo and heading
c1, c2 = st.columns([0.32, 2])
with c1:
    st.image("images/stylized-arrow-symbol-short.png", width=85)
with c2:
    st.caption("")
    st.title("Grammar Pointer")

# Initialize session state
if "valid_inputs_received" not in st.session_state:
    st.session_state["valid_inputs_received"] = False

# Sidebar
st.sidebar.image("images/Anthropic.png", width=200)
st.sidebar.title("Grammar Pointer")
gp_credential = st.sidebar.text_input(
    "Enter your Password or Anthropic API key:", 
    type="password",
    help="Once you created your Anthropic account, you can get your API access token."
)

if gp_credential:
    # check if password is valid
    if gp_credential in st.secrets.get("gp_passwords", []):
        api_key = st.secrets.get("anthropic_api_key")
    else:
        api_key = gp_credential
    os.environ["ANTHROPIC_API_KEY"] = api_key
    anthropic = Anthropic(api_key=api_key)
else:
    st.sidebar.warning("Please enter your password or Anthropic API key to use Grammar Pointer.")


st.sidebar.markdown("---")
st.sidebar.write("App created by pratic-orft using [Streamlit](https://streamlit.io/)🎈 and Anthropic Claude Sonnet 3.5.")

# Tabbed navigation
MainTab, InfoTab = st.tabs(["Main", "Info"])

with InfoTab:
    st.subheader("What is Streamlit?")
    st.markdown("[Streamlit](https://streamlit.io) is a Python library that allows the creation of interactive, data-driven web applications in Python.")
    
    st.subheader("Resources")
    st.markdown("""
    - [Streamlit Documentation](https://docs.streamlit.io/)
    - [Cheat sheet](https://docs.streamlit.io/library/cheatsheet)
    - [Book](https://www.amazon.com/dp/180056550X) (Getting Started with Streamlit for Data Science)
    """)
    
    st.subheader("Deploy")
    st.markdown("You can quickly deploy Streamlit apps using [Streamlit Community Cloud](https://streamlit.io/cloud) in just a few clicks.")

with MainTab:
    st.markdown("This app gives pointers for grammar, spelling, and punctuation in foreign languages!")
    
    MAX_CHARACTERS = 1500
    
    with st.form(key="my_form"):
        in_text = st.text_area(
            "Deutschen Text zur Prüfung eingeben",
            height=200,
            help=f"Bitte nur deutschen Text mit max. {MAX_CHARACTERS} eingeben!",
            key="1",
        )
        
        if len(in_text) > MAX_CHARACTERS:
            st.info(f"Nur die ersten {MAX_CHARACTERS} Zeichen werden geprüft.")
        
        submit_button = st.form_submit_button(label="Prüfen")
    
    if not submit_button and not st.session_state.valid_inputs_received:
        st.stop()
    elif submit_button and not in_text:
        st.warning("❄️ Kein Text zu prüfen!")
        st.session_state.valid_inputs_received = False
        st.stop()
    elif submit_button or st.session_state.valid_inputs_received:
        if submit_button:
            st.session_state.valid_inputs_received = True
        
        Claude_json_output = check_grammar(in_text)
        # st.write(Claude_json_output)
        
        try:
            test_json = json.loads(Claude_json_output)
        except ValueError:
            st.write("Text konnte nicht geprüft werden. Häufige Fehler: Sonderzeichen, Anführungszeichen etc. Diese Entfernen und Prüfung wiederholen.")
            st.stop()

        st.success("✅ Fertig!")
        
        # Create and Process the Dataframe with the Grammar Pointers
        df = pd.read_json(Claude_json_output, orient="records")
        df.dropna(how="all", inplace=True)
        df.fillna(value="", inplace=True)


        colored_sentences = process_df(df)


        # Display the results of color coding the input text
        st.caption("")
        st.markdown("### Geprüfter Text mit Anstreichungen!")
        st.markdown(body="<span style='text-decoration: underline; text-decoration-color:blue;'>Grammatik</span> - <span style='text-decoration: underline; text-decoration-color:green;'>Rechtschreibung</span> - <span style='text-decoration: underline; text-decoration-color:orange;'>Wortwahl und Wortstellung</span> - <span style='text-decoration: underline; text-decoration-color:yellow;'>Zeichensetzung</span>", unsafe_allow_html=True)
        st.caption("")

        st.markdown(colored_sentences, unsafe_allow_html=True)

        
        st.caption("")
        st.markdown("### Bitte die Ergebnisse auswerten!")
        st.caption("")
        
        # Filter Grammar Pointers before displaying 
        df_filtered = df.filter(["Satz", "Satzteil", "Fehler"], axis=1)
        df_filtered.reset_index(drop=True, inplace=True)
        df_filtered.index = df_filtered.index + 1
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1

        st.write(df_filtered)
        
    # Download button
    @st.cache_data
    def convert_df(df):
        return df.to_csv().encode("utf-8")
        
    csv = convert_df(df)
    dt_now = datetime.now()
    now = dt_now.strftime("%-d-%-m-%Y")

    # Wrap the download button in a Streamlit fragment: Streamlit labels this a temporary workaround
    @st.experimental_fragment
    def show_download_button():
        st.download_button(
        label="Ergebnisse herunterladen (CSV-Format)",
        data=csv,
        file_name=f"Grammar-Pointers-{now}.csv",
        mime="text/csv",
        )
    
    show_download_button()
    with st.spinner("3 Sekunden Pause"):
        time.sleep(3)    


# Custom CSS to improve the appearance
st.markdown("""
    <style>
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
    }
    .stTextArea > div > div > textarea {
        background-color: #f0f2f6;
    }
    .stSelectbox > div > div > select {
        background-color: #f0f2f6;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)