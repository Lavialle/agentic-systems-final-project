from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, BaseMessage, HumanMessage
from typing import Annotated, Sequence, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from summarizer_agent import summarize_law_text
from tone_analysis_agent import analyze_tone_of_voice, create_law_title
from config import OPENAI_API_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_BASE_URL
from PyPDF2 import PdfReader
import os




class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Initialiser le modèle avec ou sans Langfuse

model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    openai_api_key=OPENAI_API_KEY,
)



# Tool : Résumé des textes de loi
@tool
def summarize_tool(law_text: str):
    """Produit un résumé clair et compréhensible d'un texte de loi."""
    return summarize_law_text(law_text)

# Tool : Analyse du tone of voice
@tool
def tone_analysis_tool(law_text: str):
    """Analyse le tone of voice des médias à propos d'un texte de loi."""
    law_title = create_law_title(law_text)
    return analyze_tone_of_voice(law_title)


tools=[summarize_tool, tone_analysis_tool]
tools_by_name = {tool.name: tool for tool in tools}
llm_model_with_tools = model.bind_tools(tools)

# Define our tool node
def tool_node(state: AgentState) -> AgentState:
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=tool_result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],

            )
        )
    return {"messages": outputs}

# Define the node that calls the llm model
def call_llm_node(state: AgentState, config: RunnableConfig) -> AgentState:
    response = llm_model_with_tools.invoke(state["messages"], config=config)
    return {"messages": [response]}

# Define the condition edge that determines whether to continue or not
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    return "continue" if (hasattr(last_message, 'tool_calls') and last_message.tool_calls) else "end"

# Define a new graph
workflow = StateGraph(AgentState)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_llm_node)
workflow.add_node("tool", tool_node)

# Set the entrypoint as `agent`
workflow.add_edge(START, "agent")

# We now add a conditional edge
workflow.add_conditional_edges(  
    "agent", 
    # Mapping: keys are strings, values are nodes.The output of `should_continue` is matched to a key, and the corresponding node is then called.
    should_continue,
    {
        # If `tools`, then call the tool node.
        "continue": "tool", 
        # Otherwise finish.
        "end": END,
        },
    )
# Aller directement à END après l'exécution des tools (pas de synthèse)
workflow.add_edge("tool", END)
# Compile the graph
graph = workflow.compile()


SYSTEM_PROMPT_SIMPLE_AGENT = SystemMessage(
    content="""Assistant juridique. 2 outils disponibles :
- summarize_tool(law_text) : résume la loi
- tone_analysis_tool(law_text) : analyse presse

RÈGLE STRICTE : Tu dois choisir UN SEUL outil à la fois.
- Si résumé demandé : utilise UNIQUEMENT summarize_tool
- Si analyse presse demandée : utilise UNIQUEMENT tone_analysis_tool
- Si "les deux" demandé : choisis celui qui te semble le plus pertinent

Tu ne peux PAS appeler les deux outils simultanément."""
)

# Fonction principale pour exécuter l'agent
def run_agent(user_query: str):
    """
    Exécute l'agent avec une requête utilisateur.
    
    Args:
        user_query (str): La question ou demande de l'utilisateur.
    
    Returns:
        dict: Les messages de l'agent incluant les résultats.
    """    
    initial_state = {
        "messages": [
            SYSTEM_PROMPT_SIMPLE_AGENT,
            HumanMessage(content=user_query)
        ]
    }
    
    # Exécuter le graph avec ou sans Langfuse tracing
    result = graph.invoke(initial_state)
    return result

# Fonction pour lire un fichier PDF
def read_pdf(file_path: str) -> str:
    """
    Lit un fichier PDF et extrait son contenu textuel.
    
    Args:
        file_path (str): Chemin vers le fichier PDF.
    
    Returns:
        str: Texte extrait du PDF.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Erreur lors de la lecture du PDF : {str(e)}"

# Fonction pour exécuter l'agent avec un PDF
def run_agent_with_pdf(pdf_path: str, user_request: str):
    """
    Exécute l'agent LangGraph avec un document PDF.
    L'agent décide automatiquement quels outils utiliser.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF contenant la loi.
        user_request (str): La demande de l'utilisateur (résumé, analyse, etc.)
    
    Returns:
        str: Réponse finale de l'agent.
    """
    
    print("\n📄 Lecture du PDF...")
    law_text = read_pdf(pdf_path)
    
    if law_text.startswith("Erreur"):
        return law_text
    
    # Limiter le texte pour éviter dépassement contexte et timeouts
    MAX_CHARS = 5000
    law_text = law_text[:MAX_CHARS]
    
    print(f"✓ PDF lu avec succès ({len(law_text)} caractères)")
    print("\n🤖 L'agent analyse votre demande...\n")
    
    # Construire la requête complète avec le texte de loi
    full_query = f"{user_request}\n\nTexte de la loi :\n{law_text}"
    
    initial_state = {
        "messages": [SYSTEM_PROMPT_SIMPLE_AGENT, HumanMessage(content=full_query)]
    }
    
    # Exécuter le graph
    
    result = graph.invoke(initial_state)
    
    # Extraire les résultats des tools uniquement
    tool_results = []
    for message in result["messages"]:
        if type(message).__name__ == "ToolMessage":
            tool_results.append(f"## {message.name}\n\n{message.content}\n\n---\n")
    
    return "\n".join(tool_results) if tool_results else "Aucune réponse générée."
