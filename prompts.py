from langchain.prompts.prompt import PromptTemplate

prompt_template = """Use the data to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
Take the data as your memory use it to answer questions. The data can be from a file page, video and much more

=====
Data: {context}
======

Question: {question}
Helpful Answer:"""
QA_PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)