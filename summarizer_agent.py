from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY

# Initialiser le LLM
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.1, 
    openai_api_key=OPENAI_API_KEY,
)

def summarize_law_text(law_text):
    """
    Résumer un texte de loi.

    Args:
        law_text (str): Texte brut de la loi.

    Returns:
        str: Résumé intelligible du texte de loi.
    """
    messages = [
        SystemMessage(content="Tu es un assistant juridique spécialisé dans les lois françaises."),
        HumanMessage(content=f"""Voici un texte de loi :\n{law_text}\n
                     \nRédige un résumé clair, concis et compréhensible pour un citoyen lambda. 
                     N'hésite pas à simplifier le jargon juridique de manière pédagogique.\n\nRésumé :""")
    ]

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"law_text": law_text})

