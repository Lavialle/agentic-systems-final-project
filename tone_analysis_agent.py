from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from serpapi import Client

from config import SERP_API_KEY, OPENAI_API_KEY

llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.1, 
    openai_api_key=OPENAI_API_KEY,
)

def create_law_title(law_text: str) -> str:
    """
    Générer un titre de loi à partir du texte de la loi.

    Args:
        law_text (str): Texte brut de la loi.

    Returns:
        str: Titre généré de la loi.
    """
    messages = [
        SystemMessage(content="Tu es un assistant juridique spécialisé dans les lois françaises."),
        HumanMessage(content=f"Voici un texte de loi :\n{law_text}\n\nPropose un titre COURT (maximum 5-7 mots) et général qui permettra de trouver des articles de presse. N'utilise pas de guillemets. Donne uniquement le titre sans explication.\n\nTitre :")
    ]

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm | StrOutputParser()
    title = chain.invoke({"law_text": law_text})
    # Nettoyer le titre (retirer guillemets et caractères spéciaux)
    title = title.replace('"', '').replace("'", "").strip()
    return title

def analyze_tone_of_voice(law_title: str):
    """
    Analyser le tone of voice des médias sur un titre de loi.

    Args:
        law_title (str): Titre de la loi.

    Returns:
        str: Analyse du tone of voice des médias.
    """
    client = Client(api_key=SERP_API_KEY)
    
    # Nettoyer et simplifier le titre pour la recherche
    search_query = law_title.replace('"', '').strip()
    
    try:
        results = client.search({
            "q": search_query,
            "engine": "google_news",
            "hl": "fr",
            "gl": "fr"
        })
    except Exception as e:
        return f"Erreur lors de la recherche SerpAPI : {str(e)}"

    # Debug: afficher la structure de la réponse
    print(f"Debug - Recherche pour: {search_query}")
    print(f"Debug - Clés disponibles: {list(results.keys())}")
    
    if "error" in results:
        # Si pas de résultats, essayer avec des mots-clés plus simples
        keywords = " ".join(search_query.split()[:3])  # Prendre seulement les 3 premiers mots
        print(f"Debug - Tentative avec mots-clés simplifiés: {keywords}")
        try:
            results = client.search({
                "q": keywords,
                "engine": "google_news",
                "hl": "fr",
                "gl": "fr"
            })
        except Exception as e:
            return f"Aucun article trouvé même avec une recherche simplifiée. Le sujet est peut-être trop récent ou peu médiatisé."
    
    # Essayer différentes clés possibles pour les résultats
    articles = results.get("news_results", results.get("articles", []))
    
    if not articles:
        return f"Aucun article de presse trouvé pour '{law_title}'.\n\nCela peut signifier que :\n- La loi est très récente et n'a pas encore été couverte par la presse\n- Le titre est trop spécifique\n- Il s'agit d'un texte législatif peu médiatisé\n\nTentez avec un autre document ou reformulez le titre."
    
    print(f"Debug - Nombre d'articles trouvés: {len(articles)}")
    
    # Construire la liste des articles
    analysis = []
    articles_info = []
    
    for article in articles[:10]:  # Limiter à 10 articles pour éviter les dépassements
        title = article.get('title', 'Titre non disponible')
        source = article.get('source', {})
        if isinstance(source, dict):
            source_name = source.get('name', 'Source inconnue')
        else:
            source_name = str(source)
        link = article.get('link', 'Lien non disponible')
        
        # Pour l'analyse par le LLM
        analysis.append(f"Titre : {title}\nSource : {source_name}\nLien : {link}\n")
        
        # Pour l'affichage avec bullet points
        articles_info.append({
            'title': title,
            'source': source_name,
            'link': link
        })
    
    analysis_text = "\n\n".join(analysis)
    
    if not analysis_text.strip():
        return f"Aucune information exploitable trouvée pour '{law_title}'."

    messages = [
        SystemMessage(content="Tu es un expert en analyse médiatique."),
        HumanMessage(content=f"Voici une liste d'articles de presse concernant le titre de loi '{law_title}' :\n\n{analysis_text}\n\nAnalyse le tone of voice général des médias à propos de cette loi. En fonction du parti rattaché à ce média, déduis-en la manière dont ce texte de loi est reçu par le paysage médiatique. Justifie ton analyse.")]
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm | StrOutputParser()
    
    # Générer l'analyse
    tone_analysis = chain.invoke({"analysis_text": analysis_text})
    
    # Ajouter la liste des articles avec bullet points et liens
    articles_list = "\n\n---\n\n### 📰 Articles analysés :\n\n"
    for i, article in enumerate(articles_info, 1):
        articles_list += f"**{i}. {article['source']}** : [{article['title']}]({article['link']})\n\n"
    
    return tone_analysis + articles_list
