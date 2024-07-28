import streamlit as st
import psycopg2
import os 
import util
import logging
from dotenv import load_dotenv

load_dotenv() 

secret = os.getenv('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


conn = util.get_db_connection()

conversations = util.get_conversations(conn)
current_conversation = st.sidebar.selectbox("Select a conversation", conversations)
logging.info(f"current_conversation: {current_conversation}")

st.title("Conversation history testbench")
conversation = st.text_input("Conversation", current_conversation if current_conversation else "")

old_interactions = util.fetch_interactions(conn, conversation)
messages_length = lambda i: len(i) if len(i) > 0 else 1
num_messages = st.number_input("Number of messages in the conversation", min_value=1, max_value=20, value=messages_length(old_interactions), step=1)
interactions: list[util.Interaction] = []

cols = st.columns(2)
for i in range(num_messages):
    if i < len(old_interactions):
        human = old_interactions[i].human
        bot = old_interactions[i].bot
    else:
        human = ""
        bot = ""
    with cols[0]:
        user_msg = st.text_area(f"Message {i+1}", human)
    with cols[1]:
        bot_msg = st.text_area(f"Response {i+1}", bot)
    interactions.append(util.Interaction(human=user_msg, bot=bot_msg))

old_query = util.fetch_query(conn, conversation=conversation)
if old_query:
    q = old_query.human
else:
    q = ""
query = st.text_area(f"Query", q)
query_interaction = util.Interaction(human=query, bot="") # TODO

if st.button("Store Interactions"):
    if query.strip() == "":
        st.warning("Query can't be empty!")
    else:
        util.wipe_table(conn)
        util.store_interactions(conn=conn, interactions=interactions, conversation=conversation)
        util.store_query(conn=conn, query=query_interaction, conversation=conversation)

if st.button("Wipe Table"):
    util.wipe_db(conn)
    util.init_db(conn)