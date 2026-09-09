# MCP Tool Assistant

A practical **Model Context Protocol (MCP)** demonstration that connects an LLM with external tools using **Python, OpenRouter, Tavily, and Streamlit**.

The project demonstrates how an AI application can dynamically discover MCP tools, allow an LLM to decide when a tool is needed, execute the tool through an MCP server, and use the result to generate a final response.

## Features

- Model Context Protocol (MCP) client-server architecture
- Dynamic MCP tool discovery
- LLM-based tool calling
- OpenRouter integration with `openrouter/auto`
- Tavily web search
- Safe AST-based calculator
- Streamlit chat interface
- Stdio MCP transport
- Asynchronous MCP communication
- Automatic MCP server startup
- External API integration
- Environment-based API key management

---

## Architecture

The project consists of three main layers:

- **Streamlit UI** — handles user interaction
- **MCP Client** — communicates with the LLM and MCP server
- **MCP Server** — exposes and executes external tools

The overall architecture is:

    User
      |
      v
    Streamlit
      |
      v
    MCP Client
      |
      +-------------------+
      |                   |
      v                   v
    OpenRouter          MCP Server
       LLM                   |
                              +----------+----------+
                              |                     |
                              v                     v
                         Calculator          Tavily Search
                                                    |
                                                    v
                                               Tavily API

---

## How MCP Works in This Project

**MCP (Model Context Protocol)** provides a standardized way for AI applications to communicate with external tools and services.

In this project, the MCP client connects to the MCP server and dynamically discovers the available tools.

The workflow is:

1. The user enters a question in Streamlit.
2. The MCP client sends the question and available tool definitions to the LLM through OpenRouter.
3. The LLM decides whether a tool is required.
4. If no tool is required, the LLM generates the final answer.
5. If a tool is required, the LLM returns a structured tool call containing the tool name and arguments.
6. The MCP client sends the tool request to the MCP server.
7. The MCP server executes the selected tool.
8. The tool result is returned to the MCP client.
9. The result is sent back to the LLM.
10. The LLM generates the final response.
11. Streamlit displays the response.

The core flow is:

    User
      |
      v
    Streamlit
      |
      v
    MCP Client
      |
      v
    OpenRouter LLM
      |
      | Tool Call
      v
    MCP Client
      |
      v
    MCP Server
      |
      +---- Calculator
      |
      +---- Tavily Search
      |
      v
    Tool Result
      |
      v
    OpenRouter LLM
      |
      v
    Final Answer
      |
      v
    Streamlit

The LLM decides **which tool to use**, while the MCP server handles the **actual tool execution**.

---

## Available Tools

### Calculator

The calculator tool accepts a mathematical expression:

    calculator(expression: str)

Example request:

    Calculate 125 * 48

The LLM can generate a tool call similar to:

    calculator("125 * 48")

The result is:

    6000

Supported operations include:

- `+` Addition
- `-` Subtraction
- `*` Multiplication
- `/` Division
- `**` Power
- `%` Modulo
- Unary `+` and `-`

### Calculator Security

The calculator does not use unrestricted Python `eval()`.

Instead, it uses Python's **AST (Abstract Syntax Tree)** module to parse expressions and allow only explicitly supported mathematical operations.

This helps prevent arbitrary Python code execution through calculator input.

---

### Tavily Search

The `tavily_search` tool provides web-search functionality through Tavily.

Tool interface:

    tavily_search(query: str)

Example request:

    Search the web for information about the Model Context Protocol and summarize it.

The LLM can select `tavily_search`, provide the appropriate query, and receive the search results through the MCP server.

Current Tavily configuration:

| Setting | Value |
|---------|-------|
| Search depth | `basic` |
| Topic | `general` |
| Maximum results | `5` |
| Include answer | `true` |

The returned search information is provided to the LLM so it can generate the final response.

---

## Dynamic Tool Discovery

One of the main concepts demonstrated by this project is **dynamic tool discovery**.

The MCP client requests the available tools from the MCP server using the MCP tool-discovery mechanism:

    list_tools()

The server provides information about each tool, including:

- Tool name
- Tool description
- Input schema

The MCP client converts these definitions into the format expected by the LLM.

Currently, the server exposes:

    calculator
    tavily_search

This approach avoids manually duplicating tool definitions inside the LLM logic and makes it easier to add new MCP tools.

---

## LLM Tool Calling

The LLM does not directly execute Python functions.

Instead, it decides whether a tool is needed and returns a structured tool call.

For example:

    User:
    Calculate 25 * 16

    LLM:
    Tool = calculator
    Arguments = {"expression": "25 * 16"}

The MCP client receives this request, calls the MCP server, and returns the tool result to the LLM.

This creates a clear separation between:

- **LLM** — decides what needs to be done
- **MCP Client** — manages communication and orchestration
- **MCP Server** — executes the requested tool
- **Tool** — performs the actual operation

---

## Tool Execution Loop

The client uses a tool-calling loop because the LLM may need to call one or more tools before producing the final response.

The process can be summarized as:

    User
      |
      v
    LLM
      |
      v
    Tool required?
      |
      +---- No ----> Final Answer
      |
      Yes
      |
      v
    MCP Client
      |
      v
    MCP Server
      |
      v
    Tool
      |
      v
    Tool Result
      |
      v
    LLM
      |
      v
    Final Answer

The loop continues until the LLM decides that no additional tool calls are required.

---

## OpenRouter

The project uses **OpenRouter** as the LLM provider through its OpenAI-compatible API.

Configuration:

    Base URL:
    https://openrouter.ai/api/v1

    Model:
    openrouter/auto

The API key is loaded from the environment variable:

    OPENROUTER_API_KEY

Using `openrouter/auto` allows OpenRouter to automatically route requests to an appropriate available model.

---

## MCP Transport

The project uses **stdio transport** for communication between the MCP client and MCP server.

The MCP client automatically starts `server.py` as a subprocess and communicates with it through standard input and standard output.

The architecture is:

    MCP Client
        |
        | stdin / stdout
        v
    MCP Server Process

Because the client starts the server automatically, the server does not need to be manually started during normal application usage.

You normally only need to run:

    streamlit run app.py

---

## Project Structure

    mcp-tool-assistant/
    |
    +-- app.py
    +-- client.py
    +-- server.py
    +-- requirements.txt
    +-- README.md
    +-- .env
    +-- .gitignore
    +-- venv/

| File | Description |
|------|-------------|
| `app.py` | Streamlit frontend and user interface |
| `client.py` | MCP client, OpenRouter integration, tool discovery, and tool-calling loop |
| `server.py` | MCP server and tool implementations |
| `requirements.txt` | Python dependencies |
| `.env` | API keys and environment variables |
| `.gitignore` | Prevents sensitive and unnecessary files from being committed |
| `README.md` | Project documentation |
| `venv/` | Python virtual environment |

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python | Core programming language |
| MCP | Standardized tool communication |
| OpenRouter | LLM provider |
| OpenRouter Auto | Automatic model routing |
| Tavily | Web search |
| Streamlit | Web-based user interface |
| OpenAI SDK | OpenAI-compatible API communication |
| python-dotenv | Environment variable management |
| asyncio | Asynchronous MCP communication |
| AST | Safe mathematical expression parsing |

---

## Requirements

Before running the project, make sure you have:

- Python 3.12 or a compatible Python version
- Internet connection
- OpenRouter API key
- Tavily API key
- Git, if cloning the repository

The project uses the following dependencies:

    mcp[cli]==2.2.0
    tavily-python==0.8.1
    openai==3.8.0
    python-dotenv==1.2.3
    streamlit==1.63.0

---

## Installation

### 1. Clone the Repository

    git clone <repository-url>
    cd mcp-tool-assistant

### 2. Create a Virtual Environment

On Windows:

    python -m venv venv
    venv\Scripts\activate

On macOS/Linux:

    python3 -m venv venv
    source venv/bin/activate

### 3. Install Dependencies

    pip install -r requirements.txt

---

## Environment Variables

Create a `.env` file in the project root:

    OPENROUTER_API_KEY=your_openrouter_api_key
    TAVILY_API_KEY=your_tavily_api_key

### Environment Variable Reference

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key used to access OpenRouter |
| `TAVILY_API_KEY` | API key used to access Tavily Search |

Never commit `.env` to GitHub.

---

## Running the Application

Start the Streamlit application:

    streamlit run app.py

The application will normally be available at:

    http://localhost:8501

The MCP client automatically starts the MCP server, so you do not need to manually run:

    python server.py

---

## Usage

Once the application is running, enter a natural-language request in the Streamlit interface.

### Calculator Example

Input:

    Calculate 125 * 48

Expected tool:

    calculator

Expected result:

    6000

The result is returned to the LLM, which then generates the final response.

### Web Search Example

Input:

    Search the web for information about the Model Context Protocol and summarize it.

Expected tool:

    tavily_search

The tool sends the query to Tavily, receives search results, and returns them through the MCP server to the LLM.

### Normal Question

Input:

    What is Python?

The LLM can answer directly without using an MCP tool when external information or calculation is not required.

This demonstrates that tools are selected based on the user's request rather than being executed for every question.

---

## Security

### API Keys

API keys are stored in `.env` instead of being hard-coded into source files.

Recommended `.gitignore` entries:

    venv/
    .env
    __pycache__/
    *.pyc

### Calculator

The calculator uses restricted AST parsing instead of unrestricted `eval()` and only allows explicitly supported mathematical operations.

### External Search Content

Tavily results come from external web sources and should be treated as untrusted data rather than executable instructions.

---

## Troubleshooting

### Streamlit Does Not Start

Make sure the virtual environment is activated and dependencies are installed:

    pip install -r requirements.txt

Then run:

    streamlit run app.py

### API Key Errors

Check that `.env` exists in the project root and contains:

    OPENROUTER_API_KEY=your_openrouter_api_key
    TAVILY_API_KEY=your_tavily_api_key

Also verify that the keys are valid.

### MCP Server Errors

Make sure `server.py` exists in the expected project directory.

Normally, the server should not be started manually. Run:

    streamlit run app.py

The MCP client will start the server automatically.

### Tavily Search Errors

Check that:

- `TAVILY_API_KEY` is configured correctly.
- Internet access is available.
- The Tavily API key is valid.
- The installed Tavily package matches `requirements.txt`.

### OpenRouter Errors

Check that:

- `OPENROUTER_API_KEY` is configured correctly.
- The API key is valid.
- Internet access is available.
- `openrouter/auto` is available through your OpenRouter account.

---

## Learning Objectives

This project was built to understand the practical implementation of **Model Context Protocol and LLM tool calling**.

The main concepts demonstrated are:

- MCP client-server architecture
- Dynamic tool discovery
- LLM-based tool selection
- Structured tool calling
- MCP tool execution
- External API integration
- Asynchronous communication
- Stdio transport
- LLM and tool orchestration
- Safe tool implementation

The central concept is:

    LLM
      |
      | Decides which tool is needed
      v
    MCP Client
      |
      | Requests execution
      v
    MCP Server
      |
      | Executes tool
      v
    Tool
      |
      | Returns result
      v
    MCP Client
      |
      v
    LLM
      |
      | Generates final response
      v
    User

---

## Future Improvements

The current architecture provides a foundation for adding more tools and capabilities.

Possible improvements include:

- Add weather tools
- Add database tools
- Add file-reading tools
- Add GitHub tools
- Support multiple MCP servers
- Add persistent conversation memory
- Add tool execution logs and timeline
- Add streaming responses
- Add automated tests
- Add Docker support
- Add authentication
- Add additional MCP transports
- Add better error recovery
- Add configurable model selection
- Deploy the application

Potential future MCP tools include:

    calculator
    tavily_search
    weather
    database_query
    github_search
    file_reader
    custom API tools

---

## Key Takeaways

This project demonstrates a clear separation of responsibilities:

- **LLM** decides what needs to be done.
- **MCP Client** manages communication and orchestration.
- **MCP Server** exposes and executes tools.
- **Tools** perform specific operations.
- **External APIs** provide additional capabilities.

The architecture allows new tools to be added without tightly coupling their implementation to the main AI application.

---

## Conclusion

**MCP Tool Assistant** is a practical implementation of an AI application using **Model Context Protocol**.

It combines:

- MCP
- Dynamic tool discovery
- LLM tool calling
- OpenRouter
- Tavily
- Streamlit
- Async Python
- Stdio transport
- Safe AST-based calculation

The project demonstrates the complete lifecycle of an MCP-powered AI assistant:

    User Request
        |
        v
    LLM Decision
        |
        v
    MCP Tool Call
        |
        v
    MCP Server
        |
        v
    Tool Execution
        |
        v
    Tool Result
        |
        v
    LLM Processing
        |
        v
    Final Response

This provides a foundation for building more capable AI assistants that can interact with external tools and services through a standardized architecture.

---

## License

This project is created for educational and demonstration purposes.