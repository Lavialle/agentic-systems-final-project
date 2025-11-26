# 🏛️ Legal Assistant - French Law Analysis with LangGraph

An autonomous AI agent system for analyzing French legislative documents. The agent uses LangGraph to automatically decide which tools to use: pedagogical summary or media tone analysis.

## 📋 Features

- **PDF Upload**: Load laws, bill proposals, or legislative reports
- **Autonomous Agent**: AI automatically selects the appropriate tool
- **Pedagogical Summary**: Simplification and explanation of legal texts
- **Press Analysis**: Google News search and media tone analysis
- **Streamlit Interface**: Intuitive and interactive web interface
- **Langfuse Observability**: Complete tracing of LLM calls and agent execution

## 🏗️ Architecture

### Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface"
        UI[Streamlit App]
        PDF[PDF Upload]
        QUERY[User Query]
    end

    subgraph "LangGraph Orchestration"
        START([START])
        AGENT[Agent Node<br/>GPT-4o-mini]
        TOOL[Tool Node]
        END([END])
    end

    subgraph "Specialized Tools"
        SUMM[Summarizer Tool<br/>Pedagogical Summary]
        TONE[Tone Analysis Tool<br/>Press Analysis]
    end

    subgraph "External Services"
        OPENAI[OpenAI API<br/>GPT-4o-mini]
        SERP[SerpAPI<br/>Google News]
        LANGFUSE[Langfuse<br/>Observability]
    end

    PDF --> UI
    QUERY --> UI
    UI --> START
    START --> AGENT
    AGENT -->|Decision| TOOL
    TOOL -->|Call| SUMM
    TOOL -->|Call| TONE
    SUMM --> OPENAI
    TONE --> SERP
    TONE --> OPENAI
    TOOL --> END
    END --> UI
    AGENT -.->|Trace| LANGFUSE
    TOOL -.->|Trace| LANGFUSE

    style AGENT fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style TOOL fill:#50C878,stroke:#2E7D4E,color:#fff
    style SUMM fill:#FFB84D,stroke:#CC8A3D,color:#000
    style TONE fill:#FFB84D,stroke:#CC8A3D,color:#000
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant S as 🖥️ Streamlit
    participant P as 📄 Pipeline
    participant A as 🤖 Agent LLM
    participant T as 🔧 Tool Executor
    participant SUM as 📝 Summarizer
    participant TON as 📰 Tone Analysis
    participant API as 🌐 External APIs
    participant LF as 📊 Langfuse

    U->>S: Upload PDF + Query
    S->>P: run_agent_with_law_text(text, query)

    Note over P: Extract PDF text<br/>(max 5000 chars)

    P->>A: SystemMessage + HumanMessage
    A->>LF: Trace agent decision

    Note over A: Analyze request<br/>Select ONE tool

    alt Summary requested
        A->>T: tool_call: summarize_tool
        T->>SUM: invoke(law_text)
        SUM->>API: ChatOpenAI(GPT-4o-mini)
        SUM->>LF: Trace LLM call
        API-->>SUM: Structured summary
        SUM-->>T: ToolMessage(content)
        T->>LF: Trace tool execution
    else Press analysis requested
        A->>T: tool_call: tone_analysis_tool
        T->>TON: invoke(law_text)
        TON->>API: create_law_title()
        TON->>LF: Trace title generation
        API-->>TON: Short title
        TON->>API: SerpAPI Google News
        API-->>TON: Press articles
        TON->>API: ChatOpenAI analysis
        TON->>LF: Trace analysis
        API-->>TON: Tone analysis
        TON-->>T: ToolMessage(content)
        T->>LF: Trace tool execution
    end

    T-->>P: Result state
    P-->>S: Formatted response
    S-->>U: Display result

    Note over U,LF: Linear flow: START → Agent → Tool → END<br/>No loop for optimal speed
```

## 🚀 Installation

### Prerequisites

- Python 3.11+
- Docker (optional)
- API Keys:
  - OpenAI API Key
  - SerpAPI Key (for press analysis)
  - Langfuse Keys (optional, for observability)

### Local Setup

1. **Clone the repository**

```bash
git clone https://github.com/Lavialle/agentic-systems-final-project.git
cd agentic-systems-final-project
```

2. **Create virtual environment**

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure API keys**
   Create a `.env` file at the root:

```env
OPENAI_API_KEY=sk-...
SERP_API_KEY=your-serpapi-key
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

5. **Run the application**

```bash
streamlit run app.py
```

### Docker Setup

1. **Build and run with Docker Compose**

```bash
docker-compose up --build
```

2. **Access the application**
   Open your browser at [`http://localhost:8501`](http://127.0.0.1:8501)

3. **Stop the containers**

```bash
docker-compose down
```

## 📂 Project Structure

```
agentic-systems-final-project/
├── app.py                      # Streamlit interface
├── pipeline.py                 # LangGraph orchestration
├── summarizer_agent.py         # Summary agent
├── tone_analysis_agent.py      # Press analysis agent
├── config.py                   # API keys configuration
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image configuration
├── docker-compose.yml          # Docker Compose setup
├── .dockerignore               # Docker ignore rules
├── README.md                   # Documentation
└── data/                       # Data folder
```

## 🔧 Technical Components

### LangGraph Agent

- **StateGraph**: State management with `AgentState` (TypedDict)
- **Nodes**:
  - `agent`: LLM call with tools binding
  - `tool`: Selected tools execution
- **Edges**: START → agent → tool → END (linear flow)

### Tools (@tool decorator)

1. **summarize_tool**: Pedagogical summary with clear structure
2. **tone_analysis_tool**: Google News search + LLM analysis

### LLM Model

- **GPT-4o-mini** (OpenAI)
- Temperature: 0.1 (deterministic)
- Text limit: 5000 characters

### Observability

- **Langfuse**: Complete tracing with `@observe` decorators
- **Callbacks**: LLM calls tracking
- **Dashboard**: Real-time monitoring of agent execution

## 💡 Usage

1. **Upload a PDF** in the sidebar
2. **Ask a question**:
   - "Summarize this law"
   - "What does the press say about this law?"
   - "Analyze the media tone"
3. **The agent automatically decides** which tool to use
4. **View the result** formatted in Markdown

## 📊 Technologies Used

- **LangChain**: LLM orchestration framework
- **LangGraph**: State-based workflow graphs
- **OpenAI**: GPT-4o-mini model
- **SerpAPI**: Google News search
- **Streamlit**: Web interface
- **PyPDF2**: PDF text extraction
- **Langfuse**: LLM observability and tracing
- **Docker**: Containerization
