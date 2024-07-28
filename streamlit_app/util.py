import logging
import psycopg2
import os
import tiktoken
import streamlit as st

logger = logging.getLogger(__name__)

@st.cache_resource
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('PGVECTOR_HOST'),
        port=os.getenv('PGVECTOR_PORT'),
        database=os.getenv('PGVECTOR_DB'),
        user=os.getenv('PGVECTOR_USER'),
        password=os.getenv('PGVECTOR_PASSWORD')
    )
    init_db(conn)
    return conn


def init_db(conn, create_file: str = "create_table.sql"):
    logger.info("Initializing db")
    with open(create_file, "r") as infile: 
        sql = infile.read()
    with conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()


def wipe_db(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE Conversations;")
        conn.commit()


def get_conversations(conn) -> list[str]:
    with conn.cursor() as cur:
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
            return
        encoding = tiktoken.get_encoding('cl100k_base')
        tokens = len(encoding.encode(str(self)))
        self.tokens = tokens 
        return tokens
    
    def get_embedding(self) -> list[float]: # TODO: skipped for now for cost
        if self.embedding:
            return
        embedding = [ i/10 for i in range(1536) ]
        self.embedding = embedding 
        return embedding 


def wipe_table(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM Conversations;")
        conn.commit()


def store_interactions(conn, interactions: list[Interaction], conversation: str):
    with conn.cursor() as cur:
        for i in interactions:
            sql = """
INSERT INTO Conversations ("content", content_vector, token_count, conversation, result)
VALUES (%s, %s, %s, %s, %s)"""
            cur.execute(sql, (str(i), i.get_embedding(), i.get_tokens(), conversation, False))
            conn.commit()
    logging.info(f"{len(interactions)} stored in db.")


def store_query(conn, query: Interaction, conversation: str): 
    with conn.cursor() as cur:
        sql = """
INSERT INTO Conversations (content, content_vector, token_count, conversation, result)
VALUES (%s, %s, %s, %s, %s)"""
        cur.execute(sql, (str(query), query.get_embedding(), query.get_tokens(), conversation, True))
        conn.commit()
    logging.info(f"Query stored in db.")


def fetch_interactions(conn, conversation: str) -> list[Interaction]:
    with conn.cursor() as cur:
        cur.execute("""SELECT 
    content, 
    content_vector,
    token_count,
    result
FROM Conversations
WHERE conversation=%s
    AND result=False;""", (conversation,))
        rows = cur.fetchall()
    interactions = []
    for row in rows: 
        print(f"row: {row}")
        data = {
            "human": row[0].split('\nBot: ')[0].replace('Human: ', ''),
            "bot": row[0].split('\nBot: ')[1],
            "embedding": [ float(i) for i in row[1].replace('[', '').replace(']', '').split(',') ],
            "tokens": row[2],
            "result": row[3]
        }
        interactions.append( Interaction.from_dict(data) )
    if interactions:
        logging.info(f"Fetched {len(interactions)} interactions in conversation {conversation}.")
    else:
        logging.info(f"New conversation.")
    return interactions 


def fetch_query(conn, conversation: str) -> Interaction | None:
    with conn.cursor() as cur:
        cur.execute("""SELECT 
    content, 
    content_vector,
    token_count,
    result
FROM Conversations
WHERE conversation=%s
    AND result=True;""", (conversation,))
        rows = cur.fetchall()
    interactions = []
    for row in rows: 
        data = {
            "human": row[0].split('\nBot: ')[0].replace('Human: ', ''),
            "bot": row[0].split('\nBot: ')[1],
            "embedding": [ float(i) for i in row[1].replace('[', '').replace(']', '').split(',') ],
            "tokens": row[2],
            "result": row[3]
        }
        interactions.append( Interaction.from_dict(data) )
    ret = None
    if interactions:
        logging.info(f"Fetched {len(interactions)} interactions in conversation {conversation}.")
        assert len(interactions) == 1
        ret = interactions[0]
    else:
        logging.info(f"New conversation.")
    return ret 


def memoize(old: list[Interaction], new: list[Interaction]) -> list[Interaction]:
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
