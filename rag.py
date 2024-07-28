from dotenv import load_dotenv
import os 
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings

load_dotenv() 

secret = os.getenv('OPENAI_API_KEY')
model = ChatOpenAI(model="gpt-3.5-turbo")

# prompt_template = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful AI bot."),
#     ("placeholder", "{conversation}") # placeholder is a magic optional value
# ])

# output_parser = StrOutputParser()

# chain = prompt_template.run | model | output_parser

# output = chain.invoke(
#     {
#         "conversation": [
#             ("human", "Hi!"),
#             ("ai", "How can I assist you today?"),
#             ("human", "Can you make me an ice cream sundae?"),
#             ("ai", "No."),
#             ("human", "Why not?")
#         ]
#     }
# )

# print(output)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Response Instructions: Your response MUST begin with “!!!TRIGGER_START!!!”. Your response MUST THEN contain an outlined summarized answer (flush left in format) to the user query. Your response MUST END with “!!!TRIGGER_END!!!” on a new line."""),
    ("user", "draft a boiler plate contract")
])

output_parser = StrOutputParser()

chain = prompt_template | model | output_parser

output = chain.invoke({})

print(output)



