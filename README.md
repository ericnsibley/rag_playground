Purpose: 
This will serve as a portable and reproduceable experiment to get a feeling for RAG architectures. 

This project will be a little unorthodox. 
Instead of focusing my attention on the 'knowledge base' component of the RAG architecture, I'm going to zoom in on the conversational aspect of RAG systems. As a social species accustomed to a conversational back-and-forth, it's very disorienting when you're speaking to one of these systems and you want the current responses to reflect corrections you've already made, or you make reference to a previous statement, or you just don't want to repeat yourself. 
I'm going to set up a test bench that allows me to query my conversational history in a variety of ways to determine which results in the most consistently performing system. In order to do this, I've set up a chat application that will allow us to fill out the contents of a conversation and generate the next reponse. When we generate the next response, the conversation gets embedded and stored in a docker-compose networked pgvector instance. The app will then execute a variety of conversational searching algorithms in parallel to retrieve the relevant messages, generating the next response for each of them. They will all be displayed on the frontend for visual comparison. 

So far I've completed the functionality of the app with the database and mocked out the embeddings. 

TODO: 
embeddings
searching algorithms
generate response from llm

