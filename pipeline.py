from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, BaseMessage, HumanMessage
from typing import Annotated, Sequence, TypedDict
from langfuse import observe
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from summarizer_agent import summarize_law_text
from tone_analysis_agent import analyze_tone_of_voice, create_law_title
from config import langfuse_handler, MAX_CHARS
from PyPDF2 import PdfReader

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Initialiser le modèle
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1
)

# Tool : Résumé des textes de loi
@tool
@observe(name="summarize_tool")
def summarize_tool(law_text: str):
    """Produit un résumé clair et compréhensible d'un texte de loi."""
    return summarize_law_text(law_text)

# Tool : Analyse du tone of voice
@tool
@observe(name="tone_analysis_tool")
def tone_analysis_tool(law_text: str):
    """Analyse le tone of voice des médias à propos d'un texte de loi."""
    law_title = create_law_title(law_text)
    return analyze_tone_of_voice(law_title)


tools=[summarize_tool, tone_analysis_tool]
tools_by_name = {tool.name: tool for tool in tools}
llm_model_with_tools = model.bind_tools(tools)

# Define our tool node
def tool_node(state: AgentState) -> AgentState:
    """
    Exécute les outils sélectionnés par l'agent.
    
    Args:
        state: État actuel du graphe contenant les messages
    
    Returns:
        Dict avec les messages de résultat des outils
    """
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=tool_result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
        )
    return {"messages": outputs}

# Define the node that calls the llm model
def call_llm_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Appelle le modèle LLM avec les outils disponibles.
    
    Args:
        state: État actuel du graphe
        config: Configuration incluant les callbacks Langfuse
    
    Returns:
        Dict avec la réponse du modèle
    """
    response = llm_model_with_tools.invoke(state["messages"], config)
    return {"messages": [response]}

# Define the condition edge that determines whether to continue or not
def should_continue(state: AgentState) -> str:
    """
    Détermine si l'agent doit continuer vers les outils ou terminer.
    
    Args:
        state: État actuel du graphe
    
    Returns:
        "continue" si des outils doivent être appelés, "end" sinon
    """
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
graph = workflow.compile()

# Générer l'image PNG du graphe au démarrage
def generate_graph_png():
    """Génère une image PNG du graphe LangGraph."""
    try:
        graph_image = graph.get_graph().draw_mermaid_png()
        with open("agent_graph.png", "wb") as f:
            f.write(graph_image)
        print("✓ Graphe généré : agent_graph.png")
        return True
    except Exception as e:
        print(f"⚠️ Impossible de générer le graphe PNG : {e}")
        return False

# Générer le graphe au chargement du module
generate_graph_png()

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

# Fonction pour lire un fichier PDF
def read_pdf(file_source) -> str:
    """
    Lit un fichier PDF et extrait son contenu textuel.
    
    Args:
        file_source: Chemin vers le fichier PDF (str) ou objet fichier (UploadedFile, file-like object).
    
    Returns:
        str: Texte extrait du PDF.
    """
    try:
        reader = PdfReader(file_source)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Erreur lors de la lecture du PDF : {str(e)}"

# Fonction pour exécuter l'agent avec un texte de loi
@observe(name="run_agent_with_law_text")
def run_agent_with_law_text(law_text: str, user_request: str, max_chars: int = MAX_CHARS):
    """
    Exécute l'agent LangGraph avec un texte de loi.
    L'agent décide automatiquement quels outils utiliser.
    
    Args:
        law_text (str): Le texte de la loi à analyser.
        user_request (str): La demande de l'utilisateur (résumé, analyse, etc.)
        max_chars (int): Nombre maximum de caractères à traiter (défaut: 5000)
    
    Returns:
        str: Réponse finale de l'agent formatée en Markdown.
    """
    
    # Limiter le texte pour éviter dépassement contexte et timeouts
    law_text_truncated = law_text[:max_chars]
    
    print(f"\n🤖 L'agent analyse votre demande ({len(law_text_truncated)} caractères)...\n")
    
    # Construire la requête complète avec le texte de loi
    full_query = f"{user_request}\n\nTexte de la loi :\n{law_text_truncated}"
    
    initial_state = {
        "messages": [SYSTEM_PROMPT_SIMPLE_AGENT, HumanMessage(content=full_query)]
    }
    
    # Exécuter le graph avec Langfuse tracing
    result = graph.invoke(
        initial_state,
        config={"callbacks": [langfuse_handler]}
    )
    
    # Extraire les résultats des tools uniquement
    tool_results = []
    for message in result["messages"]:
        if type(message).__name__ == "ToolMessage":
            tool_results.append(f"## {message.name}\n\n{message.content}\n\n---\n")
    
    return "\n".join(tool_results) if tool_results else "Aucune réponse générée."