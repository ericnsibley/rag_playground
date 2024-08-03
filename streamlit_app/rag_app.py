import streamlit as st
import os 
import util
import logging
from dotenv import load_dotenv

load_dotenv() 

secret = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Rerunning page...")

util.get_db_connection()

conversations = util.get_conversations() 
current_conversation = st.sidebar.selectbox("Select a conversation", conversations)

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

st.session_state['interactions'] = util.memoize(st.session_state['old_interactions'], interactions)
st.write(len(st.session_state['interactions']))
if 'old_query' not in st.session_state:
    st.session_state['old_query'] = util.fetch_query()
if st.session_state['old_query'] is None:
    q = ""
else:
    q = st.session_state['old_query'].human
    
query = st.text_area(f"Query", q)
st.session_state['query'] = util.Interaction(human=query, bot="") # TODO


if st.button("Store Interactions", on_click=util.store_and_search_interactions):
    if query.strip() == "":
        st.warning("Query can't be empty!") # This does nothing to a callback


if st.button("Wipe Table"):
    util.wipe_db()
    util.init_db()