from typing import Annotated, Sequence, TypedDict, Literal
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from prompt_library.prompts import PROMPT_REGISTRY, PromptType
from retriever.retrieval import Retriever
from utils.model_loader import ModelLoader
from evaluation.ragas_eval import evaluate_context_precision, evaluate_response_relevancy
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import os

class AgenticRAG:
    """Agentic RAG pipeline using LangGraph + MCP (Retriever + WebSearch)."""

    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    # ---------- Initialization ----------
    def __init__(self):
        self.retriever_obj = Retriever()
        self.model_loader = ModelLoader()
        self.llm = self.model_loader.load_llm()
        self.checkpointer = MemorySaver()

        # Initialize MCP client
        mcp_url = os.getenv("MCP_URL", "http://mcp-server:8001/mcp")
        self.mcp_client = MultiServerMCPClient(
            {
                "hybrid_search": {
                    "transport": "streamable_http",
                    "url": mcp_url
                }
            }
        )
        self.mcp_tools: list = []

        # Build workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

        async def _ensure_mcp_tools(self):
            if not self.mcp_tools:
                self.mcp_tools = await self.mcp_client.get_tools()
                print("MCP tools loaded:", [t.name for t in self.mcp_tools])

    # async def async_init(self):
    #     """Load MCP tools asynchronously."""
    #     self.mcp_tools = await self.mcp_client.get_tools()

    # async def _safe_async_init(self):
    #     """Safe async init wrapper (prevents event loop crash)."""
    #     try:
    #         self.mcp_tools = await self.mcp_client.get_tools()
    #         print("MCP tools loaded successfully.")
    #     except Exception as e:
    #         print(f"Warning: Failed to load MCP tools — {e}")
    #         self.mcp_tools = []

    # ---------- Nodes ----------
    def _ai_assistant(self, state: AgentState):
        print("--- CALL ASSISTANT ---")
        messages = state["messages"]
        last_message = messages[-1].content.strip().lower()

        ecommerce_keywords = [
            "price", "buy", "cost", "review", "rating",
            "product", "iphone", "samsung", "laptop",
            "mobile", "phone", "tablet", "tv", "camera",
            "compare", "best", "budget"
        ]

        greeting_keywords = [
            "hi", "hello", "hey", "hii", "hiii",
            "good morning", "good evening", "good afternoon",
            "what can you do", "help", "who are you"
        ]

        if any(word in last_message for word in ecommerce_keywords):
            return {"messages": [HumanMessage(content="TOOL: retriever")]}

        elif any(greet in last_message for greet in greeting_keywords):
            prompt = ChatPromptTemplate.from_template(
                "You are a polite and friendly ecommerce product assistant.\n"
                "Briefly introduce yourself and explain how you can help.\n\n"
                "User: {question}\nAssistant:"
            )
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke(
                {"question": last_message}
            ) or (
                "Hi 👋 I’m your ecommerce product assistant. "
                "I can help you with product prices, reviews, comparisons, "
                "and recommendations. Just ask about any product!"
            )
            return {"messages": [HumanMessage(content=response)]}

        else:
            return {"messages": [HumanMessage(content=(
                            "I’m designed to help only with ecommerce products — "
                            "including prices, reviews, comparisons, and recommendations. "
                            "Please ask a product-related question."
                        ))]}

    async def _vector_retriever(self, state: AgentState):
        print("--- RETRIEVER (MCP) ---")
        await self._ensure_mcp_tools()
        query = state["messages"][-1].content

        tool = next((t for t in self.mcp_tools if t.name == "get_product_info"), None)
        if not tool:
            return {"messages": [HumanMessage(content="Retriever tool not found in MCP client.")]}

        try:
            result = await tool.ainvoke({"query": query})
            context = result or "No relevant product data found."
        except Exception as e:
            context = f"Error invoking retriever: {e}"

        return {"messages": [HumanMessage(content=context)]}

    async def _web_search(self, state: AgentState):
        print("--- WEB SEARCH (MCP) ---")
        await self._ensure_mcp_tools()
        query = state["messages"][-1].content
        forbidden_terms = ["launch", "rumor", "leak", "expected", "upcoming", "2026", "2027"]
        if any(term in query.lower() for term in forbidden_terms):
            return {"messages": [HumanMessage(
                        content="This product information is not available in our catalog."
                    )]}
        tool = next((t for t in self.mcp_tools if t.name == "web_search"), None)
        if not tool:
            return {"messages": [HumanMessage(content="Web search tool not found in MCP client.")]}

        result = await tool.ainvoke({"query": query})  # ✅
        context = result if result else "No data from web"
        return {"messages": [HumanMessage(content=context)]}


    def _grade_documents(self, state: AgentState) -> Literal["generator", "rewriter"]:
        print("--- GRADER ---")
        question = state["messages"][0].content
        docs = state["messages"][-1].content

        if docs and "No local results found" not in docs and len(docs) > 100:
            return "generator"

        prompt = PromptTemplate(
            template="""You are a grader. Question: {question}\nDocs: {docs}\n
            Are the docs completely irrelevant to answering the question? Answer yes or no.""",
            input_variables=["question", "docs"],
        )
        chain = prompt | self.llm | StrOutputParser()
        score = chain.invoke({"question": question, "docs": docs}) or ""
        return "rewriter" if "yes" in score.lower() else "generator"

    def _generate(self, state: AgentState):
        print("--- GENERATE ---")
        question = state["messages"][0].content
        docs = state["messages"][-1].content

        prompt = ChatPromptTemplate.from_template(
            PROMPT_REGISTRY[PromptType.PRODUCT_BOT].template
        )
        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({"context": docs, "question": question}) or "No response generated."
        except Exception as e:
            response = f"Error generating response: {e}"

        return {"messages": [HumanMessage(content=response)]}

    def _rewrite(self, state: AgentState):
        print("--- REWRITE ---")
        question = state["messages"][0].content

        prompt = ChatPromptTemplate.from_template(
            "Rewrite this user query to make it more clear and specific for a search engine. "
            "Do NOT answer the query. Only rewrite it.\n\nQuery: {question}\nRewritten Query:"
        )
        chain = prompt | self.llm | StrOutputParser()

        try:
            new_q = chain.invoke({"question": question}).strip()
        except Exception as e:
            new_q = f"Error rewriting query: {e}"

        return {"messages": [HumanMessage(content=new_q)]}

    # ---------- Build Workflow ----------
    def _build_workflow(self):
        workflow = StateGraph(self.AgentState)
        workflow.add_node("Assistant", self._ai_assistant)
        workflow.add_node("Retriever", self._vector_retriever)
        workflow.add_node("Generator", self._generate)
        workflow.add_node("Rewriter", self._rewrite)
        workflow.add_node("WebSearch", self._web_search)

        # Workflow edges
        workflow.add_edge(START, "Assistant")
        workflow.add_conditional_edges(
            "Assistant",
            lambda state: "Retriever" if "TOOL" in state["messages"][-1].content else END,
            {"Retriever": "Retriever", END: END},
        )
        workflow.add_conditional_edges(
            "Retriever",
            self._grade_documents,
            {"generator": "Generator", "rewriter": "Rewriter"},
        )
        workflow.add_edge("Generator", END)
        workflow.add_edge("Rewriter", "WebSearch")
        workflow.add_edge("WebSearch", "Generator")

        return workflow

    # ---------- Public Run ----------
    async def run(self, query: str, thread_id: str = "default_thread") -> str:
        """Run the workflow for a given query and return the final answer."""
        result = await self.app.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        return result["messages"][-1].content

# ---------- Standalone Test ----------
if __name__ == "__main__":
    rag_agent = AgenticRAG()
    answer = rag_agent.run("What is the price of iPhone 16?")
    print("\nFinal Answer:\n", answer)
