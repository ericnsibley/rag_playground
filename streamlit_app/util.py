import logging
import psycopg2
import os
import tiktoken
import streamlit as st
from openai import OpenAI

logger = logging.getLogger(__name__)

# @st.cache_resource # Durable through faults is better than caching a connection
# cache_resource on a pool is probably even better though
def get_db_connection():
    if 'db_conn' not in st.session_state or st.session_state['db_conn'].closed:
        logger.info("Getting new db connection.")
        st.session_state['db_conn'] = psycopg2.connect(
            host=os.getenv('PGVECTOR_HOST'),
            port=os.getenv('PGVECTOR_PORT'),
            database=os.getenv('PGVECTOR_DB'),
            user=os.getenv('PGVECTOR_USER'),
            password=os.getenv('PGVECTOR_PASSWORD')
        )
        init_db()
    else: 
        logger.info("Reusing db connection.")


def init_db(create_file: str = "create_table.sql"):
    logger.info("Initializing db")
    with open(create_file, "r") as infile: 
        sql = infile.read()
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute(sql)
        st.session_state['db_conn'].commit()


def wipe_db():
    logger.info(f"Wiping db.")
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("DROP TABLE Conversations;")
        st.session_state['db_conn'].commit()


def get_conversations() -> list[str]:
    logger.info(f"Getting distinct conversations")
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("SELECT DISTINCT conversation FROM Conversations;")
        rows = cur.fetchall()
    return [ row[0] for row in rows ]


class Interaction:
    def __init__(self, human: str, bot: str, embedding: list[float] | None = None, tokens: int | None = None, result: bool = False) -> None:
        self.human = human.strip()
        self.bot = bot.strip()
        self.embedding = embedding 
        self.tokens = tokens
        self.result = result

    @classmethod
    def from_dict(cls, data: dict[str, any]):
        return cls(**data)

    def __str__(self):
        return f"""Human: {self.human}
Bot: {self.bot}"""
    
    def get_tokens(self) -> int:
        if self.tokens:
            return self.tokens
        encoding = tiktoken.get_encoding('cl100k_base')
        tokens = len(encoding.encode(str(self)))
        self.tokens = tokens 
        return tokens
    
    def get_embedding(self) -> list[float]: 
        if self.embedding:
            return self.embedding 
        if self.result:
            text = self.human
        else:
            text = str(self)
        print(f"text: {text}")
        client = OpenAI(api_key=st.session_state['openai_api_key'])
        embedding = [ i/10 for i in range(1536) ]
        self.embedding = embedding 
        return embedding 


def wipe_table():
    logging.info("Wiping table.")
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("DELETE FROM Conversations;")
        st.session_state['db_conn'].commit()


def store_interactions():
    with st.session_state['db_conn'].cursor() as cur:
        for i in st.session_state['interactions']:
            sql = """
INSERT INTO Conversations ("content", content_vector, token_count, conversation, result)
VALUES (%s, %s, %s, %s, %s)"""
            cur.execute(sql, (str(i), i.get_embedding(), i.get_tokens(), st.session_state.convo, False))
            st.session_state['db_conn'].commit()
    logger.info(f"{len(st.session_state['interactions'])} stored in db.")


def store_query(): 
    with st.session_state['db_conn'].cursor() as cur:
        sql = """
INSERT INTO Conversations (content, content_vector, token_count, conversation, result)
VALUES (%s, %s, %s, %s, %s)"""
        cur.execute(sql, (str(st.session_state['query']), st.session_state['query'].get_embedding(), st.session_state['query'].get_tokens(), st.session_state.convo, True))
        st.session_state['db_conn'].commit()
    logger.info(f"Query stored in db.")


def fetch_interactions() -> list[Interaction]:
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("""SELECT 
    content, 
    token_count,
    content_vector,
    result
FROM Conversations
WHERE conversation=%s
    AND result=False
ORDER BY timestamp;""", (st.session_state.convo,))
        rows = cur.fetchall()
    interactions = db_rows_to_interactions(rows)
    if interactions:
        logger.info(f"Fetched {len(interactions)} interactions in conversation {st.session_state.convo}.")
    else:
        logger.info(f"No interactions to fetch, new conversation.")
    return interactions 


def fetch_query() -> Interaction | None:
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("""SELECT 
    content, 
    token_count,
    content_vector,
    result
FROM Conversations
WHERE conversation=%s
    AND result=True;""", (st.session_state.convo,))
        rows = cur.fetchall()
    interactions = db_rows_to_interactions(rows)
    ret = None
    if interactions:
        logger.info(f"Fetched {len(interactions)} query in conversation {st.session_state.convo}.")
        assert len(interactions) == 1
        ret = interactions[0]
    else:
        logger.info(f"No query, new conversation.")
    return ret 


row_get = lambda row, index, default=None: row[index] if index < len(row) else default
def db_rows_to_interactions(rows) -> list[Interaction]:
    interactions = []
    for row in rows: 
        data = {
            "human": row[0].split('\nBot: ')[0].replace('Human: ', ''),
            "bot": row[0].split('\nBot: ')[1],
            "tokens": row[1],
            "embedding": [ float(i) for i in row[2].replace('[', '').replace(']', '').split(',') ] if row_get(row, 2) else None,
            "result": row_get(row, 3)
        }
        interactions.append( Interaction.from_dict(data) )
    return interactions


def memoize(old: list[Interaction], new: list[Interaction]) -> list[Interaction]: # optimize the common case to reduce costs
    ret = []
    o_len = len(old)
    n_len = len(new)
    for i in range(n_len):
        if i < o_len:
            if old[i].human == new[i].human and old[i].bot == new[i].bot:
                ret.append( old[i] )
        else:
            ret.append( new[i] )
    return ret 


MAX_TOKENS = 500
def search_by_similarity(embedding: list[float], max_tokens: int = MAX_TOKENS) -> list[Interaction]:
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("""
WITH Similar_messages AS (
    SELECT 
        content,
        token_count,
        SUM(token_count) OVER (ORDER BY 1 - (content_vector <=> %s::vector) ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_tokens 
    FROM Conversations
    WHERE conversation = %s
        AND result = False
)
SELECT
    content, 
    token_count
FROM Similar_messages
WHERE cumulative_tokens <= %s;""", (embedding, st.session_state.convo, max_tokens)) 
        rows = cur.fetchall()
    interactions = db_rows_to_interactions(rows)
    if interactions:
        logger.info(f"Similarity search fetched {len(interactions)} interactions in conversation {st.session_state.convo}.")
    else:
        logger.info(f"No conversation to search.")
    return interactions 


def search_by_recent(max_tokens: int = MAX_TOKENS) -> list[Interaction]:
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("""
WITH Ranked_conversations AS (
    SELECT 
        content,
        token_count,
        SUM(token_count) OVER (ORDER BY timestamp DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_tokens 
    FROM Conversations
    WHERE conversation = %s
        AND result = False
)
SELECT 
    content, 
    token_count
FROM Ranked_conversations
WHERE cumulative_tokens <= %s;""", (st.session_state.convo, max_tokens)) 
        rows = cur.fetchall()
    interactions = db_rows_to_interactions(rows)
    if interactions:
        logger.info(f"Recency search fetched {len(interactions)} interactions in conversation {st.session_state.convo}.")
    else:
        logger.info(f"No conversation to search.")
    return interactions 


def search_by_recent_and_similarity(embedding: list[float], recent_message_limit: int = 1, max_tokens: int = MAX_TOKENS) -> list[Interaction]:
    with st.session_state['db_conn'].cursor() as cur:
        cur.execute("""
WITH Recent_messages AS (
    SELECT 
        content,
        token_count,
        timestamp,
        SUM(token_count) OVER (ORDER BY timestamp DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_tokens
    FROM Conversations
    WHERE conversation=%s
        AND result=False
    LIMIT %s
),
Filtered_recent_messages AS (
    SELECT 
        content,
        token_count,
        timestamp,
        cumulative_tokens
    FROM Recent_messages
    WHERE cumulative_tokens <= %s
),
Recent_token_sum AS (
    SELECT COALESCE(SUM(token_count), 0) AS tokens FROM Filtered_recent_messages
),
Similar_messages AS (
    SELECT 
        content,
        token_count,
        SUM(token_count) OVER (ORDER BY 1 - (content_vector <=> %s::vector) ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_tokens
    FROM Conversations
    WHERE conversation = %s
        AND result = False
        AND timestamp NOT IN (SELECT timestamp FROM Filtered_recent_messages)
),
Filtered_similar_messages AS (
	SELECT
		content, 
		token_count,
		cumulative_tokens
	FROM Similar_messages, Recent_token_sum
	where cumulative_tokens + Recent_token_sum.tokens <= %s
)
SELECT 
    content,
    token_count
FROM Filtered_recent_messages
UNION ALL
SELECT 
    content,
    token_count
FROM Filtered_similar_messages;""", (st.session_state.convo, recent_message_limit, max_tokens, embedding, st.session_state.convo, max_tokens)) 
        rows = cur.fetchall()
    interactions = db_rows_to_interactions(rows)
    if interactions:
        logger.info(f"Blended search fetched {len(interactions)} interactions in conversation {st.session_state.convo}.")
    else:
        logger.info(f"No conversation to search.")
    return interactions 


def get_completion(interactions: list[Interaction], query: str, max_tokens: int = 500, model: str = 'gpt-3.5-turbo'):
    client = OpenAI(api_key=st.session_state['openai_api_key'])
    p = ""
    for i in interactions:
        p += str(i) + '\n\n'

    prompt = f"""I need help rephrasing a query. I will send you parts of a conversation along with a query, and you will rephrase the query into context. 

Previous interactions:
{p}

Query:
{query}

Please take into account the context from the previous chats when rephrasing the query."""
    
    res = client.chat.completions.create(
        model=model,
        messages=[
            { "role": "user", "content": prompt }
        ],
        max_tokens=max_tokens
    )
    return res.choices[0].message.content
