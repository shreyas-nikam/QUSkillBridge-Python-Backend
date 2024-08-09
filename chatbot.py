from langchain.prompts import PromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_openai.chat_models import ChatOpenAI
from retriever import Retriever
import os
from dotenv import load_dotenv
import logging
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
import json

load_dotenv()

class ChatBot:
    """
    Class to handle the chatbot functionality.

    Attributes:
    OPENAI_KEY (str): The OpenAI key.
    OPENAI_MODEL (str): The OpenAI model.
    embeddings (OpenAIEmbeddings): The OpenAI embeddings.
    chat_model (ChatOpenAI): The OpenAI chat model.
    chat_history (str): The chat history.
    """
    def __init__(self, db_path):
        """
        The constructor for the ChatBot class.
        """
        
        self.OPENAI_KEY = os.environ.get("OPENAI_KEY") 
        self.OPENAI_MODEL =  os.environ.get("OPENAI_MODEL")
        self.embeddings = OpenAIEmbeddings(api_key=self.OPENAI_KEY)
        self.chat_model = ChatOpenAI(temperature=0, model_name=self.OPENAI_MODEL, openai_api_key=self.OPENAI_KEY)
        self.retriever = Retriever(db_path)
        self.retriever._load_params()
    
    def get_question_context(self, question):
        """
        Function to get the context for the given question.
        
        Args:
        question (str): The question.
        
        Returns:
        str: The context for the question.
        """
        logging.info(f"Getting the context for the question: {question}")
        return self.retriever.parse_response_with_rerank(question)
    
    def resolve_question(self, chat_history, question):
        """
        Function to resolve the question using the ambiguity resolution prompt.

        Args:
        question (str): The question.

        Returns:
        str: The resolved question.
        """
        logging.info(f"Resolving the ambiguity for the question: {question}")
        # Create the language model
        llm = ChatOpenAI(model=self.OPENAI_MODEL, temperature=0, api_key=self.OPENAI_KEY)
    
        # Load the ambiguity resolution prompt
        ambiguity_resolution_prompt = json.load(open("data/prompts.json", "r"))["AMBIGUITY_RESOLUTION_PROMPT"]
        prompt = PromptTemplate(
            template=ambiguity_resolution_prompt,
            input_variables=["history", "question"]
        )
        
        # Format the prompt
        _input = prompt.format_prompt(history=chat_history, question=question)

        # Get the response
        output = llm(_input.to_messages())
        return output.content

    def get_response(self, history, question):
        """
        Function to get the response to the given question.

        Args:
        question (str): The question.

        Returns:
        dict: The response to the question.
        """
        print(f"Getting the response for the question: {question}")
        # Resolve the question
        question = self.resolve_question(history, question)
        print(f"Resolved question: {question}")

        # Create the output parser
        response_schemas = [
                ResponseSchema(name="answer", description="Your answer to the given question in markdown format", type = 'markdown'),
                ResponseSchema(name="follow_up_questions", description="A list of 3 follow-up questions that the user may have based on the question.", type = 'list')
            ]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        # Get the context
        context = self.get_question_context(question)
        print(f"Context: {context}")
        print(f"Context for the question {question}: {context}")
        # Get the response prompt
        response_prompt = json.load(open("data/prompts.json", "r"))["RESPONSE_PROMPT"]


        # Create the prompt
        prompt = ChatPromptTemplate(
            messages=[
                HumanMessagePromptTemplate.from_template(response_prompt)
            ],
            input_variables=["history", "context", "question"],
            partial_variables={"format_instructions": format_instructions}
        )

        # Format the prompt
        _input = prompt.format_prompt(history=history, context=context, question=question)

        print(f"Input: {_input.to_messages()}")

        # Get the response
        output = self.chat_model(_input.to_messages())

        print(output)
        
        valid_json = False
        runs = 0
        while (valid_json == False):
            try:
                # Parse the output
                json_output = output_parser.parse(output.content)
                valid_json = True
                print(f"Response for the question {question}: {output.content}")

                # Update the chat history
                history += f"""\n
                User: {question}
                You: {str(json_output['answer'])}"""

            except Exception as e:
                # If the output is not in JSON format, regenerate the answer for 5 runs
                logging.warning(f"Error in parsing the response for the question {question}: {e}")
                runs+=1
                if runs < 4:

                    # Load the error prompt
                    retry_prompt = json.load(open("data/prompts.json", "r"))["RETRY_PROMPT"]
                    error_prompt = ChatPromptTemplate(
                        messages=[
                                HumanMessagePromptTemplate.from_template(retry_prompt)
                                ],
                        input_variables=["e","history","context","question"],
                        partial_variables={"format_instructions": format_instructions}
                    )

                    # Format the error prompt
                    _error_input = error_prompt.format_prompt(e=e, history=history, context = context, question=question)

                    # Get the response
                    output = self.chat_model(_error_input.to_messages())

                # If the answer cannot be generated, return an error message
                else:
                    return {'answer': f"Something went wrong! Please try again!",
                        'follow_up_questions': []}
                    
        return json_output