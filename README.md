# 📝 Drafter

A conversational AI assistant that helps you create ATS-optimized resumes and cover letters using OpenAI and LangGraph.

## ✨ Features

- **Interactive Resume Creation** - Conversational interface to gather your information
- **ATS Optimization** - Tailors your resume to specific job descriptions
- **Cover Letter Generation** - Creates personalized cover letters for target positions
- **Document Management** - Preview, update, and save documents as DOCX files
- **Version Control** - Automatic versioning of all document changes
- **Bilingual Support** - Works with English and Taglish

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/drafter.git
cd drafter
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

4. **Run the application**
```bash
python main.py
```

## 📦 Dependencies

```
python-dotenv
langchain-openai
langchain-core
langgraph
python-docx
```

Install all at once:
```bash
pip install python-dotenv langchain-openai langchain-core langgraph python-docx
```

## 💡 Usage

### Basic Workflow

1. **Start the assistant**
```bash
python drafter_agentv2.py
```

2. **Create a resume**
```
💬 You: make me a resume
