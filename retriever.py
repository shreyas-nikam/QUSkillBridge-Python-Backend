2# Import the required libraries
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers.document_compressors import CohereRerank
from langchain.retrievers import ContextualCompressionRetriever
import pickle
import os
from dotenv import load_dotenv

# Create the logger object
import logging


load_dotenv()

# Laod the secrets
OPENAI_KEY = os.environ.get("OPENAI_KEY")
COHERE_API_KEY = os.environ.get("COHERE_API_KEY")


class Retriever:
    """
    Functionality to retrieve the documents using the hybrid retriever.

    Attributes:
    bm25_retriever: The BM25 retriever.
    vector_store: The vector store.
    faiss_retriever: The FAISS retriever.
    embeddings: The OpenAI embeddings.
    re_ranker: The Cohere re-ranker.
    params_loaded: Whether the parameters are loaded or not.
    """
    def __init__(self, db_path):
        """
        The constructor for the Retriever class.
        """
        self.bm25_retriever = None
        self.vector_store = None
        self.faiss_retriever = None
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_KEY)
        self.re_ranker = CohereRerank(cohere_api_key=COHERE_API_KEY)
        self.params_loaded = False
        self.compression_retriever = None
        self.retriever_db_path = db_path
        self.hybrid_db_path = f"{db_path}/hybrid_db"

        
    def create_vector_store(self, file_name="sample.txt"):
        """
        The function to create the vector store.

        Args:
        file_name (str): The name of the file to create the vector store.
        """

        # Load the documents
        loader = TextLoader(file_name, encoding='UTF-8')
        documents = loader.load()

        # Split the Documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)

        # Create the vector store
        self.vector_store = FAISS.from_documents(docs, self.embeddings)

        # Save the vector store
        self.vector_store.save_local(self.db_path)

        # Create the retriever
        self.bm25_retriever = BM25Retriever.from_documents(docs)
        self.bm25_retriever.k=5

        self._save_params()
        self.params_loaded = True

    def _save_params(self):
        """
        Function to save the parameters.
        """
        # Store the retrievers and vector store to be used later
        with open(f"{self.retriever_db_path}/bm25_retriever.pkl", "wb") as f:
            pickle.dump(self.bm25_retriever, f)
        with open(f"{self.retriever_db_path}/faiss_retriever.pkl", "wb") as f:
            pickle.dump(self.faiss_retriever, f)

    def _load_params(self):
        """
        Function to load the parameters.
        """

        # Load the embeddings, retrievers and vector store which were saved earlier
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_KEY)
        self.vector_store = FAISS.load_local(self.hybrid_db_path, self.embeddings)
        self.re_ranker = CohereRerank(cohere_api_key=COHERE_API_KEY)

        with open(f"{self.retriever_db_path}/bm25_retriever.pkl", "rb") as f:
            self.bm25_retriever = pickle.load(f)
        with open(f"{self.retriever_db_path}/faiss_retriever.pkl", "rb") as f:
            self.faiss_retriever = pickle.load(f)

        # Load the retrievers for use
        faiss_retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, faiss_retriever], 
            weights=[0.5, 0.5]
        )

        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.re_ranker, 
            base_retriever=ensemble_retriever
        )
        
        self.params_loaded = True
    

    def _retrieve_with_rerank(self, query):
        """
        Function to retrieve the documents using the re-ranker.

        Args:
        query (str): The query to retrieve the documents.

        Returns:
        list: The list of documents retrieved.
        """
        logging.debug(f"Query: {query}")
        # Load the retrievers if they are not loaded
        if self.params_loaded == False:
            self._load_params()
        
        # Get the response
        if self.compression_retriever is None:
            self._load_params()

        response = self.compression_retriever.invoke(query)
        return response
    
    def parse_response_with_rerank(self, query):
        """
        Function to parse the response from the re-ranker.

        Args:
        query (str): The query to retrieve the documents.

        Returns:
        str: The parsed response.
        """
        # Get the response
        response = self._retrieve_with_rerank(query)
        logging.debug(f"Response for query {query}: {response}")
        
        # Parse and return the response
        return '\n\n'.join([r.page_content for r in response])
    

