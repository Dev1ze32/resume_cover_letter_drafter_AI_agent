# 📄 DRAFTER - Resume & Cover Letter Assistant

my first langchain-langgraph project

A conversational AI agent that helps you create professional resumes and cover letters through natural dialogue.

## ✨ Features

- **Smart Resume Generation** - Creates professional resumes from your information
- **Personalized Cover Letters** - Tailors cover letters to specific jobs and companies
- **Document Updates** - Modify sections of your documents
- **Auto-Save** - Saves your documents to text files
- **Taglish Support** - Understands English and Philippine dialects

## 🚀 Quick Start

### Prerequisites

```bash
pip install langchain langchain-openai langgraph python-dotenv
```

### Setup

1. Create a `.env` file:
```
OPENAI_MODEL=gpt-4.0mini
OPENAI_API_KEY=your_api_key_here
```

2. Create a `prompts.py` file with these functions:
   - `get_resume_prompt(name, title, summary, experience, education, skills)`
   - `get_cover_letter_prompt(name, title, summary, experience, education, skills, job_title, company, tone)`
   - `get_main_reply_prompt()`
   - prompts already in inside

3. Run the agent:
```bash
python drafter_agent.py
```

## 💬 Usage Example

```
You: I need a resume

AI: Sure! I'll need some details:
- Name:
- Job Title:
- Summary:
- Experience:
- Education:
- Skills:

You: [Provide your information]

AI: [Creates resume]

You: Update the experience section

AI: [Updates the section]

You: Save it

AI: ✓ Saved successfully
  • Resume → resume.txt
```

## 🛠️ Available Tools

| Tool | Description |
|------|-------------|
| `create_resume` | Generates a professional resume |
| `create_cover_letter` | Creates a tailored cover letter |
| `update` | Modifies document sections |
| `save` | Saves documents to files |

## 📁 Output Files

- **resume.txt** - Your generated resume
- **letter.txt** - Your cover letter
- can tell ai the name of txt

## 🎯 Design Philosophy

- **Conversational First** - Natural dialogue, not forms
- **Smart Clarification** - Asks for missing details before generating
- **Focused Purpose** - Only handles resume/cover letter tasks
- **No Assumptions** - Never invents information

## 🔒 Guardrails

DRAFTER is strictly focused on professional documents. It will politely decline:
- Programming help
- General knowledge questions
- Unrelated tasks

## 📝 Notes

- Documents are stored in memory during the session
- The agent asks clarifying questions for vague information
- Supports custom tones for cover letters (e.g., formal, enthusiastic)
- Auto-saves with default filenames unless specified

---

**Made with LangChain + LangGraph** 🦜🕸️
