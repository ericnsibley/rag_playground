import streamlit as st
import os 
import util
import logging
from dotenv import load_dotenv
import json

load_dotenv() 

secret = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Rerunning page...")

util.get_db_connection()

conversations = util.get_conversations() 

with st.sidebar:
    current_conversation = st.selectbox("Select a conversation", conversations)

    openai_api_key = st.text_input("OpenAI API Key", key="openai_api_key", type="password")

st.title("Conversation history testbench")

st.text_input("Conversation", current_conversation if current_conversation else "", key='convo')

if 'old_interactions' not in st.session_state:
    st.session_state['old_interactions'] = util.fetch_interactions()

messages_length = lambda i: len(i) if len(i) > 0 else 1
num_messages = st.number_input("Number of messages in the conversation", min_value=1, max_value=20, value=messages_length(st.session_state.old_interactions), step=1)
interactions: list[util.Interaction] = []

cols = st.columns(2)
for i in range(num_messages):
    if i < len(st.session_state.old_interactions):
        human = st.session_state.old_interactions[i].human
        bot = st.session_state.old_interactions[i].bot
    else:
        human = ""
        bot = ""
    with cols[0]:
        user_msg = st.text_area(f"Message {i+1}", human)
    with cols[1]:
        bot_msg = st.text_area(f"Response {i+1}", bot)

    interaction = util.Interaction(human=user_msg, bot=bot_msg)
    if interaction.human != "" and interaction.bot != "":
        interactions.append( interaction )

# reduce embedding costs by reusing them
st.session_state['interactions'] = util.memoize(st.session_state['old_interactions'], interactions)

if 'old_query' not in st.session_state:
    st.session_state['old_query'] = util.fetch_query()

if st.session_state['old_query'] is None:
    q = ""
    b = ""
else:
    q = st.session_state['old_query'].human
    b = st.session_state['old_query'].bot
    
query = st.text_area(f"Query", q)
st.session_state['query'] = util.Interaction(human=query, bot=b)


if st.button("Save and regenerate"):
    if st.session_state['query'] == "":
        st.warning("Query can't be empty.")
        st.stop()

    if st.session_state['openai_api_key'] == "":
        st.warning("Please add your OpenAI API key to continue.")
        st.stop()

    util.wipe_table()
    util.store_interactions()

    if st.session_state['query'].human != "": #TODO: consider asyncio-ing these
        di = {}
        interactions = util.search_by_recent()
        di['recency'] = util.get_completion(interactions, st.session_state['query'].human)
        interactions = util.search_by_similarity(st.session_state['query'].get_embedding())
        di['similarity'] = util.get_completion(interactions, st.session_state['query'].human)
        interactions = util.search_by_recent_and_similarity(st.session_state['query'].get_embedding())
        di['blended'] = util.get_completion(interactions, st.session_state['query'].human)
        st.session_state['query'].bot = json.dumps(di)
        print(di)
        util.store_query()


if st.session_state['query'].bot != "":
    searches = json.loads(st.session_state['query'].bot)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div style='background-color: #F08080; padding: 10px; border-radius: 10px;'>Recency:<br>{searches.get('recency', '')}</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background-color: #6CA6CD; padding: 10px; border-radius: 10px;'>Similarity:<br>{searches.get('similarity', '')}</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background-color: #7ACB7A; padding: 10px; border-radius: 10px;'>Blended:<br>{searches.get('blended', '')}</div>", unsafe_allow_html=True)


if st.button("Wipe DB"):
    util.wipe_db()
    util.init_db()