from typing import Annotated, TypedDict, Sequence, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import os

from prompts import get_main_reply_prompt, get_resume_prompt, get_cover_letter_prompt
from helper.document_helper import DocumentStore, DocumentType


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('drafter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Centralized configuration - easier to test and modify"""
    model_name: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    temperature: float = 0.5
    max_tokens: int = 250
    output_dir: Path = field(default_factory=lambda: Path("./outputs"))
    
    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True)


class AgentState(TypedDict):
    """Enhanced state with metadata"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    document_store: DocumentStore
    config: AgentConfig
    user_context: dict  # Store user info to avoid re-asking

class DocumentGenerator:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.model = ChatOpenAI(
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    def generate_resume(self, name: str, title: str, summary: str, 
                       experience: str, education: str, skills: str, certifications:Optional[str] = None, portfolio:Optional[str] = None) -> str:
        """Generate resume with error handling"""
        try:
            prompt = get_resume_prompt(name, title, summary, experience, education, skills, certifications, portfolio)
            response = self.model.invoke([SystemMessage(content=prompt)])
            logger.info(f"Generated resume for {name}")
            return response.content
        except Exception as e:
            logger.error(f"Resume generation failed: {e}")
            raise ValueError(f"Failed to generate resume: {str(e)}")
    
    def generate_cover_letter(self, name: str, title: str, summary: str,
                             experience: str, education: str, skills: str,
                             job_title: str, company: str, tone: str) -> str:
        """Generate cover letter with error handling"""
        try:
            # Use higher temperature for more creative cover letters
            creative_model = ChatOpenAI(
                model_name=self.config.model_name,
                temperature=0.7,
                max_tokens=self.config.max_tokens
            )
            prompt = get_cover_letter_prompt(
                name, title, summary, experience, education, skills,
                job_title, company, tone
            )
            response = creative_model.invoke([SystemMessage(content=prompt)])
            logger.info(f"Generated cover letter for {company}")
            return response.content
        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            raise ValueError(f"Failed to generate cover letter: {str(e)}")


# Tools with dependency injection
def create_tools(document_store: DocumentStore, generator: DocumentGenerator, config: AgentConfig):
    """Factory function for tools - enables testing with mock dependencies"""
    
    @tool(description="""
        Generate a professional resume draft based on the user's background.
        Requires: name, title, summary, experience, education, and skills.
        optional: portfolio and certification (if they dont have then just proceed)
        Returns: Formatted resume with version tracking.
    """)
    def create_resume(name: str, title: str, summary: str, experience: str, 
                     education: str, skills: str, certifications:Optional[str] = None, portfolio:Optional[str] = None) -> str:
        try:
            content = generator.generate_resume(name, title, summary, experience, education, skills, certifications, portfolio)
            metadata = document_store.create(DocumentType.RESUME, content)
            
            return (
                f"✓ Resume Created Successfully\n\n"
                f"Version: {metadata.version}\n"
                f"Word Count: {metadata.word_count}\n"
                f"Created: {metadata.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Preview:\n{content[:200]}..."
            )
        except Exception as e:
            logger.error(f"create_resume failed: {e}")
            return f"✗ Error creating resume: {str(e)}"
    
    @tool(description="""
        Write a personalized cover letter tailored to a specific job.
        Requires: name, title, summary, experience, education, skills, job_title, company, tone.
        Tone options: professional, enthusiastic, formal, creative.
    """)
    def create_cover_letter(name: str, title: str, summary: str, experience: str,
                           education: str, skills: str, job_title: str, 
                           company: str, tone: str = "professional") -> str:
        try:
            content = generator.generate_cover_letter(
                name, title, summary, experience, education, skills,
                job_title, company, tone
            )
            metadata = document_store.create(DocumentType.COVER_LETTER, content)
            
            return (
                f"✓ Cover Letter Created Successfully\n\n"
                f"Target: {company} - {job_title}\n"
                f"Version: {metadata.version}\n"
                f"Word Count: {metadata.word_count}\n"
                f"Tone: {tone}\n\n"
                f"Preview:\n{content[:200]}..."
            )
        except Exception as e:
            logger.error(f"create_cover_letter failed: {e}")
            return f"✗ Error creating cover letter: {str(e)}"
    
    @tool(description="""
        Save documents to DOCX files with automatic naming and versioning.
        Supports: resume, cover_letter, or both (if both exist).
    """)
    def save_documents(document_types: Optional[list[str]] = None) -> str:
        """Save documents as DOCX files with smart defaults and better feedback"""
        try:
            if document_types is None:
                # Save all existing documents
                document_types = [dt.value for dt in DocumentType if document_store.exists(dt)]
            
            if not document_types:
                return "✗ No documents to save. Create a resume or cover letter first."
            
            saved = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for doc_type_str in document_types:
                try:
                    doc_type = DocumentType(doc_type_str)
                    metadata = document_store.get(doc_type)
                    
                    if not metadata:
                        continue
                    
                    # Change extension to .docx
                    filename = f"{doc_type.value}_{timestamp}_v{metadata.version}.docx"
                    filepath = config.output_dir / filename
                    
                    # Use the new DOCX save function
                    DocumentStore.save_to_docx(metadata.content, filepath, doc_type)
                    
                    saved.append(f"{doc_type.value.title()} → {filepath}")
                    logger.info(f"Saved {doc_type.value} to {filepath}")
                    
                except ValueError:
                    logger.warning(f"Invalid document type: {doc_type_str}")
            
            if not saved:
                return "✗ No valid documents found to save."
            
            return "✓ Saved Successfully (DOCX format):\n  • " + "\n  • ".join(saved)
            
        except Exception as e:
            logger.error(f"save_documents failed: {e}")
            return f"✗ Error saving documents: {str(e)}"
    
    @tool(description="""
        Update an existing document with new content.
        Preserves version history and tracks changes.
        document_type: 'resume' or 'cover_letter'
    """)
    def update_document(document_type: str, content: str) -> str:
        try:
            doc_type = DocumentType(document_type)
            
            if not document_store.exists(doc_type):
                return f"✗ No {doc_type.value} exists yet. Create one first."
            
            old_metadata = document_store.get(doc_type)
            new_metadata = document_store.create(doc_type, content)
            
            return (
                f"✓ {doc_type.value.title()} Updated\n\n"
                f"Version: {old_metadata.version} → {new_metadata.version}\n"
                f"Word Count: {old_metadata.word_count} → {new_metadata.word_count}\n\n"
                f"Preview:\n{content[:200]}..."
            )
        except ValueError:
            return f"✗ Invalid document type: {document_type}. Use 'resume' or 'cover_letter'."
        except Exception as e:
            logger.error(f"update_document failed: {e}")
            return f"✗ Error updating document: {str(e)}"
    
    @tool(description="Preview the current version of a document without saving")
    def preview_document(document_type: str) -> str:
        try:
            doc_type = DocumentType(document_type)
            metadata = document_store.get(doc_type)
            
            if not metadata:
                return f"✗ No {doc_type.value} exists yet."
            
            return (
                f"📄 {doc_type.value.title()} Preview\n"
                f"{'=' * 60}\n"
                f"Version: {metadata.version}\n"
                f"Word Count: {metadata.word_count}\n"
                f"Last Modified: {metadata.last_modified.strftime('%Y-%m-%d %H:%M')}\n"
                f"{'=' * 60}\n\n"
                f"{metadata.content}"
            )
        except ValueError:
            return f"✗ Invalid document type: {document_type}"
        except Exception as e:
            return f"✗ Error previewing: {str(e)}"
    
    return [create_resume, create_cover_letter, save_documents, update_document, preview_document]


def build_agent_graph(config: AgentConfig) -> StateGraph:
    """Build the LangGraph workflow with enhanced routing"""
    
    document_store = DocumentStore()
    generator = DocumentGenerator(config)
    tools = create_tools(document_store, generator, config)
    
    model = ChatOpenAI(
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    ).bind_tools(tools)
    
    def agent_node(state: AgentState) -> AgentState:
        """Main agent logic with context awareness"""
        system_prompt = get_main_reply_prompt()
        
        # Initialize state
        state.setdefault("messages", [])
        state.setdefault("document_store", document_store)
        state.setdefault("config", config)
        
        messages = state["messages"]
        
        # If last message is a ToolMessage, AI responds without asking for input
        if messages and isinstance(messages[-1], ToolMessage):
            all_messages = [SystemMessage(content=system_prompt)] + messages
            
            try:
                response = model.invoke(all_messages)
                
                # Only print if there's actual content
                if response.content and response.content.strip():
                    print(f"\nAssistant: {response.content}")
                
                state["messages"].append(response)
                
            except Exception as e:
                logger.error(f"Agent node error after tool: {e}")
                error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Please try again.")
                state["messages"].append(error_msg)
                print(f"\nError: {str(e)}")
            
            return state
        
        # Get user input
        user_input = input("\n💬 You: ").strip()
        
        # Handle empty input
        if not user_input:
            return state
        
        if user_input.lower() in ['quit', 'exit', 'bye', 'end']:
            logger.info("User requested exit")
            print("\n👋 Goodbye! Thanks for using Drafter.")
            state["_exit_requested"] = True
            return state
        
        user_message = HumanMessage(content=user_input)
        all_messages = [SystemMessage(content=system_prompt)] + state["messages"] + [user_message]
        
        try:
            response = model.invoke(all_messages)
            
            # Only print if there's actual content
            if response.content and response.content.strip():
                print(f"\nAssistant: {response.content}")
            
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_names = [tc['name'] for tc in response.tool_calls]
                print(f"\n🔧 Calling tools: {', '.join(tool_names)}")
                logger.info(f"Tools invoked: {tool_names}")
            
            state["messages"].append(user_message)
            state["messages"].append(response)
            
        except Exception as e:
            logger.error(f"Agent node error: {e}")
            error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Please try again.")
            state["messages"].append(user_message)
            state["messages"].append(error_msg)
            print(f"\nError: {str(e)}")
        
        return state
    
    def route_agent(state: AgentState) -> Literal["use_tools", "continue_chat", "end"]:
        """Intelligent routing based on message history"""
        
        # Check exit flag first
        if state.get("_exit_requested", False):
            logger.info("Routing to END (exit requested)")
            return "end"
        
        messages = state.get("messages", [])
        
        if not messages:
            logger.info("No messages, routing to continue_chat")
            return "continue_chat"
        
        last_message = messages[-1]
        logger.info(f"Last message type: {type(last_message).__name__}")
        
        # Route to tools if AI wants to use them
        if isinstance(last_message, AIMessage):
            # Check if tool_calls exists AND is not empty
            tool_calls = getattr(last_message, 'tool_calls', None)
            has_tool_calls = tool_calls is not None and len(tool_calls) > 0
            logger.info(f"AIMessage has tool_calls: {tool_calls}")
            
            if has_tool_calls:
                tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else tc['name'] for tc in tool_calls]
                logger.info(f"ROUTING TO TOOLS: {tool_names}")
                return "use_tools"
        
        # If last message is ToolMessage, go back to agent to respond
        if isinstance(last_message, ToolMessage):
            logger.info("ROUTING BACK TO AGENT (after tool execution)")
            return "continue_chat"
        
        # Otherwise continue normal chat (ask for input)
        logger.info("ROUTING TO CONTINUE_CHAT (normal flow)")
        return "continue_chat"
    
    # Build graph
    graph = StateGraph(AgentState)
    
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools=tools))
    
    graph.set_entry_point("agent")
    
    graph.add_conditional_edges(
        "agent",
        route_agent,
        {
            "use_tools": "tools",
            "continue_chat": "agent",
            "end": END
        }
    )
    
    # After tools execute, ALWAYS go back to agent
    graph.add_edge("tools", "agent")
    
    return graph.compile()


def run_document_agent():
    """Enhanced CLI with better UX"""
    load_dotenv()
    config = AgentConfig()
    
    print("\n" + "=" * 70)
    print("         📝 DRAFTER - Professional Resume & Cover Letter Assistant")
    print("=" * 70)
    print("  I can help you create, edit, and save professional documents.")
    print("  Type 'quit', 'exit', or 'bye' to end the session.")
    print("=" * 70 + "\n")
    
    logger.info("Starting Drafter session")
    
    app = build_agent_graph(config)
    state = {
        "messages": [],
        "document_store": DocumentStore(),
        "config": config
    }
    
    try:
        for step in app.stream(state, stream_mode="values"):
            # Stream handles display, just track state
            state = step
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("         ⚠️  SESSION INTERRUPTED BY USER")
        print("=" * 70)
        logger.info("Session interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.error(f"Runtime error: {e}", exc_info=True)
    finally:
        print("\n" + "=" * 70)
        print("         ✓ DRAFTER SESSION ENDED")
        print(f"         Output saved to: {config.output_dir}")
        print("=" * 70 + "\n")
        logger.info("Session ended")


if __name__ == "__main__":
    run_document_agent()