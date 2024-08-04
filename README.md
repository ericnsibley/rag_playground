## What is it? 
This will serve as a portable and reproduceable experiment for evaluating implementations of chat history storage and retrieval. This project zooms into the area of RAG architectures involving storing previous conversation and retrieving it for the intent of rephrasing the current query into conversational context. 

Because we are narrowing the scope to a small part of the architecture, this project is a little unorthodox. Instead of a comfortable back-and-forth in an ordinary chat app, the user sets up a conversation all the way up to a final generation, and then we get a generation for each conversation-retrieval strategy for comparison.  

This idea was inspired by a team from Google implementing RAG for work. They built a conversation history store out of Firestore that operates solely on context stuffing the most recent message until a token limit is met. I took a look at [how langchain implements it](https://python.langchain.com/v0.1/docs/use_cases/question_answering/chat_history/) and saw that they make use of another vector store. 

This made two things click for me 
- if the cornerstone of RAG architectures is a vector database, then I always have at least one in a RAG system
- I use the vector DB to similarity search for answers and I want to start performing similarity search on conversation history. I should probably be using a similar backend flow to implement similar functionality

## Why do we care?
As a social species accustomed to a conversational back-and-forth, it's very disorienting when you're speaking to one of these systems and you want the current responses to reflect corrections you've already made, or you make reference to a previous statement, or you just don't want to repeat yourself. This project allow us to compare multiple strategies of retrieving conversation history and see which generates good output the most consistently. 
But why did I make a weird variation on the chat application that every engineer has programmed a million times before? 
I find that in life, given enough time, nature nearly always follows the path of least resistance. If the correct thing to do is also the harder thing to do, oftentimes I see corners being cut. I see architectures implemented without determining if each piece is working well first. 
My theory is that because performing this sort of experiment in a traditional RAG app is difficult, I hadn't seen it done before. Or perhaps because it was difficult, it only happened behind closed doors within private companies. To combat this I have created an app that makes performing this comparison easy.  


## How does it work? 

The user sets up a conversation by formatting the interactions in the UI. Since RAG apps function purely as one-shot call-and-response it was easy to generalize that pattern and make a UI that facillitates this data entry.  
Then when a response is generated, each interaction in the conversation receives an embedding that encodes the semantic content of the back-and-forth exchange, and the interactions get and stored in a docker-compose networked pgvector instance. Then the query receives an embedding on just the query portion, which can be used for a similarity comparison against the interaction embeddings. The app will then execute a variety of conversational searching algorithms to retrieve the relevant messages, rephrasing the query into context for each search. The rephrased queries are all displayed on the frontend for visual comparison. 

## Takeaways: 

I really like making use of metadata to pre-filter the results before similarity searching. Vector search is relatively slow (we use ANN algorithms over deterministic NN; if the database has to cut a corner and make the results potentially worse to make the outcome reasonably fast, then we should help it when we can or risk running into scaling issues down the line). I've been dabbling with other vector db vendors but this is my first experience building with pgvector, and being able to natively filter on my data within the Postgres SQL engine feels so much more powerful. I may not be going back.

# TODO: 
- embeddings
    - put off until end to save on costs, but it is now the end
    - ada 2 has limit of 8191 token input, make sure interactions respect that limit and fail gracefully 
- deployment
- env vars in deployment
- thrash db, save stuff that matches your api key from env vars
- maybe asyncio to parallelize the searches? 



