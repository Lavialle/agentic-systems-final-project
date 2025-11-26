import streamlit as st
from PyPDF2 import PdfReader
from pipeline import run_agent_with_law_text, read_pdf
from config import MAX_CHARS

# Configuration de la page
st.set_page_config(
    page_title="Assistant Juridique - Analyse de Lois",
    page_icon="🏛️",
    layout="wide"
)

# Titre de l'application
st.title("🏛️ Assistant Juridique")
st.markdown("### Analysez vos documents législatifs avec l'IA")

# Sidebar pour l'upload du document
with st.sidebar:
    st.header("📄 Document")
    uploaded_file = st.file_uploader(
        "Uploadez votre document PDF",
        type=["pdf"],
        help="Téléchargez une loi, proposition de loi ou rapport législatif"
    )
    
    if uploaded_file:
        st.success(f"✓ Fichier chargé : {uploaded_file.name}")
        st.info(f"Taille : {uploaded_file.size / 1024:.2f} KB")

# Interface principale
if uploaded_file is None:
    st.info("👈 Commencez par uploader un document PDF dans la barre latérale")
    
    # Instructions
    st.markdown("""
    ### Comment utiliser cette application ?
    
    1. **Uploadez un document PDF** contenant :
        - Une loi
        - Une proposition de loi
        - Un rapport législatif
    
    2. **Posez votre question** à l'agent IA :
        - L'agent décide automatiquement quels outils utiliser
        - Il peut résumer la loi, analyser la presse, ou les deux
        - Exemples : "Résume cette loi", "Que dit la presse ?", "Fais les deux"
    
    3. **Consultez la réponse** générée par l'agent
    """)

else:
    # Extraction du texte depuis le fichier uploadé (une seule fois)
    with st.spinner("📄 Lecture du document..."):
        law_text = read_pdf(uploaded_file)
    
    if law_text.startswith("Erreur"):
        st.error(law_text)
    else:
        # Afficher des informations sur le document
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Caractères", f"{len(law_text):,}")
        with col2:
            st.metric("Mots", f"{len(law_text.split()):,}")
        with col3:
            st.metric("Pages", len(PdfReader(uploaded_file).pages))
        
        # Limiter le texte pour éviter le dépassement du contexte et les timeouts
        law_text_truncated = law_text[:MAX_CHARS]
        
        if len(law_text) > MAX_CHARS:
            st.warning(f"⚠️ Le document est long ({len(law_text):,} caractères). Seuls les premiers {MAX_CHARS:,} caractères seront analysés.")
        
        st.divider()
        
        # Mode Agent
        st.subheader("🤖 Assistant Agent IA")
        st.info("💡 L'agent analyse votre demande et choisit automatiquement l'outil le plus approprié (résumé OU analyse de presse).")
        st.warning("L'agent ne peut exécuter qu'UN seul outil à la fois.")
        
        user_query = st.text_input(
            "💬 Que voulez-vous savoir sur cette loi ?",
            placeholder="Ex: Résume cette loi OU Analyse la presse",
            key="agent_query"
        )
        
        # Bouton d'analyse
        if st.button("🚀 Lancer l'agent", type="primary", use_container_width=True, disabled=not user_query):
            
            if not user_query:
                st.warning("⚠️ Veuillez poser une question sur le document ci-dessus.")
            else:
                # Human-in-the-loop: afficher la confirmation
                st.markdown("---")
                st.subheader("⚠️ Confirmation")
                st.write(f"**Votre demande :** {user_query}")
                st.write(f"**Document :** {uploaded_file.name}")
                st.write(f"**Taille du texte :** {len(law_text_truncated):,} caractères")
                
                with st.spinner("🤖 L'agent analyse votre demande et sélectionne les outils..."):
                    try:
                        # Exécuter l'agent avec le texte déjà extrait
                        agent_response = run_agent_with_law_text(
                            law_text_truncated, 
                            user_query,
                            max_chars=MAX_CHARS
                        )
                        
                        st.success("✓ L'agent a terminé son analyse")
                        st.markdown("---")
                        st.markdown("### 📋 Réponse de l'agent")
                        st.markdown(agent_response)
                        
                        # Bouton de téléchargement
                        st.download_button(
                            label="⬇️ Télécharger la réponse",
                            data=agent_response,
                            file_name=f"agent_response_{uploaded_file.name.replace('.pdf', '.txt')}",
                            mime="text/plain"
                        )
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'exécution de l'agent : {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        <p>Développé avec ❤️ | Powered by LangChain & OpenAI</p>
    </div>
    """,
    unsafe_allow_html=True
)