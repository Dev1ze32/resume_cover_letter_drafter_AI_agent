from typing import Annotated, TypedDict, Sequence
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.messages import ToolMessage
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import os

from prompts import get_resume_prompt, get_cover_letter_prompt, get_main_reply_prompt

load_dotenv()
ai_model = os.getenv("OPENAI_MODEL")
resume_document = ""
cover_letter_document = ""

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

#TOOLS
@tool(description="""
    Generate a professional resume draft based on the user's background, skills, and experience.
      This tool should only be use when name, title, summary, experience, education, and skills information is taken
      """)
def create_resume(name: str, title:str, summary: str, experience: str, education: str, skills:str):
    global resume_document
    resume_model = ChatOpenAI(
    model_name=ai_model,
    temperature=0.5,
    max_tokens=500  # Increased for complete output
    )
    
    prompt_text = get_resume_prompt(name, title, summary, experience, education, skills)
    
    resume_ai = resume_model.invoke([SystemMessage(content=prompt_text)])
    resume_document = resume_ai.content
    return f"Resume Created\n\nResume content:\n{resume_document}"

@tool(description="""
    Write a personalized cover letter tailored to a specific job title and company.
      This tool should only be use when name, title, summary, experience, education, and skills information is taken
      """)
def create_cover_letter(name: str, title:str, summary: str, experience: str, education: str, skills:str, job_title:str, company:str, tone:str):
    global cover_letter_document
    cover_letter_model = ChatOpenAI(
    model_name=ai_model,
    temperature=0.7,
    max_tokens=500  # Increased for complete output
    )
    prompt_text = get_cover_letter_prompt(name, title, summary, experience, education, skills, job_title, company, tone)
    
    cover_letter_ai = cover_letter_model.invoke([SystemMessage(content=prompt_text)])
    cover_letter_document = cover_letter_ai.content
    return f"Cover Letter Created\n\nCover Letter content:\n{cover_letter_document}"

    
@tool(description="Save the current document(s) to text file(s)")
def save(letter_filename: str = None, resume_filename: str = None) -> str:
    global cover_letter_document
    global resume_document
    
    saved_files = []
    errors = []
    
    # Save cover letter if it exists
    if cover_letter_document:
        letter_filename = "letter.txt"
        try:
            with open(letter_filename, 'w', encoding='utf-8') as file:
                file.write(cover_letter_document)
            saved_files.append(f"Cover Letter → {letter_filename}")
        except Exception as e:
            errors.append(f"Cover Letter: {str(e)}")
    
    # Save resume if it exists
    if resume_document:
        resume_filename = "resume.txt"
        try:
            with open(resume_filename, 'w', encoding='utf-8') as file:
                file.write(resume_document)
            saved_files.append(f"Resume → {resume_filename}")
        except Exception as e:
            errors.append(f"Resume: {str(e)}")
    
    # Handle no content case
    if not cover_letter_document and not resume_document:
        return "Error: No document content to save. Please create a resume or cover letter first."
    
    # Build response message
    response_parts = []
    if saved_files:
        response_parts.append("✓ Saved successfully\n  • " + "\n  • ".join(saved_files))
    if errors:
        response_parts.append("✗ Errors occurred\n  • " + "\n  • ".join(errors))
    
    return "\n\n".join(response_parts)
    
@tool(description="""
    Update the document with the provided content for specific file_category: resume or cover_letter 
      only update depends on the passed file only if cover_letter or resume
""")
def update(content: str, file_category:str) -> str:
    global resume_document
    global cover_letter_document
    if file_category == "resume":
        resume_document = content  # Replace instead of append for updates
        return f"Resume updated!\n\nUpdated content:\n{content}"
    elif file_category == "cover_letter":
        cover_letter_document = content
        return f"Cover Letter updated!\n\nUpdated content:\n{content}"
    else:
        return f"Invalid file category: {file_category}. Use 'resume' or 'cover_letter'."

tools = [create_cover_letter, create_resume, save, update]

model = ChatOpenAI(
    model_name=ai_model,
    temperature=0.5,
    max_tokens=500  # Increased for better responses
).bind_tools(tools)

def our_agent(state: AgentState) -> AgentState:
    system_prompt = get_main_reply_prompt()
    
    # Ensure messages exists
    state.setdefault("messages", [])

    # 🗣️ Get user input normally, even if it's the first message
    user_input = input("\nYou: ")
    user_message = HumanMessage(content=user_input)

    # Combine system + conversation
    all_messages = [SystemMessage(content=system_prompt)] + state["messages"] + [user_message]

    response = model.invoke(all_messages)

    # Display AI response (if any text content)
    if response.content:
        print(f"\nAI: {response.content}")
    
    # Display tools being called
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"\n🔧 Tools called: {[tc['name'] for tc in response.tool_calls]}")

    # Store conversation for next turn
    state["messages"].extend([user_message, response])
    return state

def agent_router(state: AgentState):
    """Check if agent wants to use tools"""
    messages = state["messages"]
    
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "use_tools"
    
    return "continue_chat"

def tools_router(state: AgentState):
    """Route after tool execution for resume/cover letter workflow"""
    messages = state["messages"]

    # Check messages in reverse to get the most recent tool call
    for message in reversed(messages[-5:]):  # Check last 5 messages
        if isinstance(message, ToolMessage):
            # Check if save was successful
            if "saved successfully" in message.content.lower():
                return "end"
    
    # Continue to agent for more interaction
    return "continue"

# Build graph
graph = StateGraph(AgentState)

graph.add_node("agent", our_agent)
graph.add_node("tools", ToolNode(tools=tools))

graph.set_entry_point("agent")

graph.add_conditional_edges(
    "agent",
    agent_router,
    {
        "use_tools": "tools",
        "continue_chat": "agent",
        "end": END
    }
)

graph.add_conditional_edges(
    "tools",
    tools_router,
    {
        "continue": "agent",
        "end": END
    }
)

app = graph.compile()

def print_messages(messages):
    """Display tool results with full content"""
    if not messages:
        return
    
    # Get the most recent tool message
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            print(f"\n{'='*60}")
            print(f"🛠️ TOOL RESULT:")
            print(f"{'='*60}")
            print(message.content)  # Print FULL content, no truncation
            print(f"{'='*60}\n")
            break  # Only show the most recent tool result

def run_document_agent():
    print("\n" + "="*60)
    print("         DRAFTER - Resume & Cover Letter Assistant")
    print("="*60)
    print("I can help you create professional resumes and cover letters!")
    print("="*60 + "\n")
    
    state = {"messages": []}
    
    try:
        for step in app.stream(state, stream_mode="values"):
            if "messages" not in step:
                continue

            messages = step["messages"]
            if not messages:
                continue

            last = messages[-1]

            # ✅ Print tool call names ONLY
            if hasattr(last, "tool_calls") and last.tool_calls:
                tool_names = [tc["name"] for tc in last.tool_calls]
                print(f"\n🔧 Tools called: {tool_names}")

            # ❌ Skip tool results completely - no printing for ToolMessage

    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("         SESSION ENDED BY USER")
        print("="*60)
    
    print("\n" + "="*60)
    print("         DRAFTER FINISHED")
    print("="*60 + "\n")

if __name__ == "__main__": run_document_agent()