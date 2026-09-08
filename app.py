import ast
import asyncio
import json
import sys
import traceback
from typing import Optional

import streamlit as st

from client import process_query

# On Windows, Streamlit's Tornado server sets asyncio's SelectorEventLoop
# policy - but SelectorEventLoop cannot spawn subprocesses. client.py's
# Client(StdioServerParameters(...)) launches server.py as a subprocess
# over stdio, so without forcing ProactorEventLoop here first, that spawn
# fails with NotImplementedError deep inside the MCP SDK's internal
# anyio TaskGroup - which is exactly the opaque "unhandled errors in a
# TaskGroup (1 sub-exception)" message you were seeing.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

MAX_RESULT_CHARS = 1500


def md(content: str) -> None:
    """Render an HTML/markdown block.

    Streamlit's markdown parser treats lines indented by 4+ spaces as a
    code block. Since our HTML strings inherit Python's own indentation,
    that was causing raw tags to be printed instead of rendered, and an
    unrendered <style> block was collapsing oddly at the top of the page.
    Stripping each line's leading whitespace fixes both issues without
    changing any markup or logic.
    """
    lines = [line.lstrip() for line in content.strip("\n").split("\n")]
    st.markdown("\n".join(lines), unsafe_allow_html=True)


def describe_error(error: BaseException) -> str:
    """Unwrap asyncio.TaskGroup / ExceptionGroup wrappers to find the real
    underlying error(s) instead of showing the opaque "1 sub-exception"
    summary Python prints by default."""
    sub_exceptions = getattr(error, "exceptions", None)
    if sub_exceptions:
        return " | ".join(describe_error(sub) for sub in sub_exceptions)
    return f"{type(error).__name__}: {error}"


def parse_structured(raw) -> Optional[object]:
    """Try to turn a raw tool result into real JSON so it can be rendered
    with st.json instead of dumped as one giant unreadable line of text."""
    if isinstance(raw, (dict, list)):
        return raw

    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text or text[0] not in "{[":
        return None

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None

    return parsed if isinstance(parsed, (dict, list)) else None


def render_tool_call(tool: dict, expanded: bool = False) -> None:
    """Render one MCP tool call: arguments plus a readable tool result.

    Raw results (e.g. scraped search text) can be huge, unstructured, and
    full of ads/boilerplate, so this pretty-prints JSON-like results and
    truncates long plain-text ones instead of dumping everything raw.
    """
    with st.expander(f"🔧  MCP Tool Executed · {tool['tool']}", expanded=expanded):
        st.markdown("**Arguments**")
        st.json(tool["arguments"])

        st.markdown("**Tool Result**")

        structured = parse_structured(tool["result"])
        if structured is not None:
            st.json(structured, expanded=False)
            return

        text = str(tool["result"]).strip()
        truncated = len(text) > MAX_RESULT_CHARS
        preview = text[:MAX_RESULT_CHARS]

        st.text_area(
            "Tool result",
            value=preview + ("…" if truncated else ""),
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )

        if truncated:
            st.caption(
                f"Showing first {MAX_RESULT_CHARS:,} of {len(text):,} characters."
            )


st.set_page_config(
    page_title="MCP Tool Assistant",
    page_icon="🔌",
    layout="wide",
    initial_sidebar_state="expanded",
)


md(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 10%, rgba(124, 58, 237, 0.12), transparent 28%),
            radial-gradient(circle at 90% 20%, rgba(6, 182, 212, 0.10), transparent 25%),
            #080b12;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stAppViewContainer"] .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 1.5rem;
    }

    [data-testid="stSidebar"] {
        background: #0b0f18;
        border-right: 1px solid rgba(255,255,255,0.07);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }

    .main-container {
        max-width: 1150px;
        margin: 0 auto;
        padding: 10px 20px 130px 20px;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 8px;
    }

    .brand-icon {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        background: linear-gradient(135deg, #7c3aed, #06b6d4);
        box-shadow: 0 0 30px rgba(124,58,237,0.35);
    }

    .brand-title {
        font-size: 27px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.8px;
    }

    .brand-subtitle {
        color: #94a3b8;
        font-size: 13px;
        margin-top: 2px;
    }

    .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-top: 22px;
        padding: 7px 13px;
        border-radius: 999px;
        background: rgba(34,197,94,0.08);
        border: 1px solid rgba(34,197,94,0.22);
        color: #86efac;
        font-size: 12px;
        font-weight: 600;
    }

    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 10px #22c55e;
    }

    .hero {
        margin-top: 35px;
        padding: 42px;
        border-radius: 24px;
        background:
            linear-gradient(135deg, rgba(124,58,237,0.14), rgba(6,182,212,0.06)),
            rgba(15,23,42,0.72);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 25px 80px rgba(0,0,0,0.25);
    }

    .hero h1 {
        margin: 0;
        font-size: 42px;
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -1.5px;
        color: #f8fafc;
    }

    .hero h1 span {
        background: linear-gradient(90deg, #a78bfa, #22d3ee);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero p {
        max-width: 720px;
        margin-top: 16px;
        color: #94a3b8;
        font-size: 15px;
        line-height: 1.7;
    }

    .architecture {
        margin-top: 25px;
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        align-items: center;
    }

    .architecture-card {
        padding: 15px 10px;
        text-align: center;
        border-radius: 13px;
        background: rgba(15,23,42,0.85);
        border: 1px solid rgba(255,255,255,0.07);
    }

    .architecture-icon {
        font-size: 20px;
        margin-bottom: 7px;
    }

    .architecture-title {
        color: #e2e8f0;
        font-size: 11px;
        font-weight: 600;
    }

    .architecture-arrow {
        text-align: center;
        color: #64748b;
        font-size: 17px;
    }

    .section-title {
        margin-top: 35px;
        margin-bottom: 15px;
        color: #f8fafc;
        font-size: 17px;
        font-weight: 700;
    }

    .tool-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
    }

    .tool-card {
        padding: 20px;
        border-radius: 18px;
        background: rgba(15,23,42,0.72);
        border: 1px solid rgba(255,255,255,0.07);
        transition: 0.2s ease;
    }

    .tool-card:hover {
        border-color: rgba(124,58,237,0.4);
        transform: translateY(-2px);
    }

    .tool-icon {
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 11px;
        background: rgba(124,58,237,0.15);
        font-size: 18px;
        margin-bottom: 13px;
    }

    .tool-name {
        color: #f1f5f9;
        font-weight: 700;
        font-size: 14px;
    }

    .tool-description {
        color: #64748b;
        font-size: 12px;
        line-height: 1.5;
        margin-top: 6px;
    }

    .chat-section {
        margin-top: 35px;
        padding: 25px;
        border-radius: 22px;
        background: rgba(10,15,25,0.65);
        border: 1px solid rgba(255,255,255,0.06);
    }

    .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 18px;
    }

    .chat-title {
        color: #f8fafc;
        font-size: 18px;
        font-weight: 700;
    }

    .model-badge {
        padding: 6px 10px;
        border-radius: 8px;
        background: rgba(124,58,237,0.12);
        border: 1px solid rgba(124,58,237,0.2);
        color: #c4b5fd;
        font-size: 10px;
        font-weight: 600;
    }

    .tool-result {
        margin: 8px 0 18px 0;
        padding: 14px;
        border-radius: 12px;
        background: #080c14;
        border: 1px solid rgba(124,58,237,0.16);
    }

    .tool-result-header {
        color: #a78bfa;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .footer {
        margin-top: 45px;
        text-align: center;
        color: #475569;
        font-size: 11px;
    }

    div[data-testid="stChatInput"] {
        background: rgba(15,23,42,0.92);
        border: 1px solid rgba(124,58,237,0.25);
        border-radius: 16px;
    }

    div[data-testid="stChatInput"]:focus-within {
        border-color: rgba(124,58,237,0.7);
        box-shadow: 0 0 25px rgba(124,58,237,0.12);
    }

    [data-testid="stExpander"] {
        background: #080c14;
        border: 1px solid rgba(124,58,237,0.16);
        border-radius: 12px;
    }

    [data-testid="stTextArea"] textarea {
        background: #05070c;
        color: #cbd5e1;
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        font-family: 'JetBrains Mono', 'Menlo', monospace;
        font-size: 12px;
        line-height: 1.6;
    }

    .sidebar-brand {
        padding: 8px 4px 25px 4px;
    }

    .sidebar-logo {
        font-size: 28px;
    }

    .sidebar-title {
        color: #f8fafc;
        font-size: 18px;
        font-weight: 800;
        margin-top: 8px;
    }

    .sidebar-description {
        color: #64748b;
        font-size: 12px;
        line-height: 1.6;
        margin-top: 6px;
    }

    .sidebar-section {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 10px;
        font-weight: 700;
        margin: 25px 0 10px 0;
    }

    .sidebar-tool {
        padding: 11px 12px;
        margin-bottom: 8px;
        border-radius: 11px;
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.05);
    }

    .sidebar-tool-name {
        color: #cbd5e1;
        font-size: 12px;
        font-weight: 600;
    }

    .sidebar-tool-desc {
        color: #475569;
        font-size: 10px;
        margin-top: 4px;
    }

    @media (max-width: 800px) {
        .architecture {
            grid-template-columns: 1fr;
        }

        .architecture-arrow {
            display: none;
        }

        .tool-grid {
            grid-template-columns: 1fr;
        }

        .hero {
            padding: 25px;
        }

        .hero h1 {
            font-size: 32px;
        }
    }
    </style>
    """
)


with st.sidebar:
    md(
        """
        <div class="sidebar-brand">
            <div class="sidebar-logo">🔌</div>
            <div class="sidebar-title">MCP Tool Assistant</div>
            <div class="sidebar-description">
                An LLM-powered application demonstrating
                Model Context Protocol tool integration.
            </div>
        </div>
        """
    )

    md('<div class="sidebar-section">System</div>')

    md(
        """
        <div class="sidebar-tool">
            <div class="sidebar-tool-name">● MCP Server</div>
            <div class="sidebar-tool-desc">Python MCP SDK · stdio transport</div>
        </div>

        <div class="sidebar-tool">
            <div class="sidebar-tool-name">● LLM</div>
            <div class="sidebar-tool-desc">OpenRouter · openrouter/auto</div>
        </div>

        <div class="sidebar-tool">
            <div class="sidebar-tool-name">● Web Search</div>
            <div class="sidebar-tool-desc">Tavily Search API</div>
        </div>
        """
    )

    md('<div class="sidebar-section">Available MCP Tools</div>')

    md(
        """
        <div class="sidebar-tool">
            <div class="sidebar-tool-name">🧮 calculator</div>
            <div class="sidebar-tool-desc">
                Safely evaluates mathematical expressions.
            </div>
        </div>

        <div class="sidebar-tool">
            <div class="sidebar-tool-name">🌐 tavily_search</div>
            <div class="sidebar-tool-desc">
                Searches the web and returns relevant sources.
            </div>
        </div>
        """
    )

    md('<div class="sidebar-section">Architecture</div>')

    md(
        """
        <div class="sidebar-tool">
            <div class="sidebar-tool-name">Streamlit</div>
            <div class="sidebar-tool-desc">User interface</div>
        </div>

        <div class="sidebar-tool">
            <div class="sidebar-tool-name">MCP Client</div>
            <div class="sidebar-tool-desc">Tool communication</div>
        </div>

        <div class="sidebar-tool">
            <div class="sidebar-tool-name">MCP Server</div>
            <div class="sidebar-tool-desc">Tool provider</div>
        </div>
        """
    )


md('<div class="main-container">')


md(
    """
    <div class="brand">
        <div class="brand-icon">🔌</div>
        <div>
            <div class="brand-title">MCP Tool Assistant</div>
            <div class="brand-subtitle">
                Model Context Protocol · Tool Calling · AI Agents
            </div>
        </div>
    </div>

    <div class="status">
        <span class="status-dot"></span>
        MCP Server Ready
    </div>
    """
)


md(
    """
    <div class="hero">
        <h1>
            Give your <span>LLM</span><br>
            access to real tools.
        </h1>

        <p>
            A working Model Context Protocol demonstration where an
            OpenRouter-powered LLM discovers and uses tools exposed by
            a Python MCP server.
        </p>

        <div class="architecture">

            <div class="architecture-card">
                <div class="architecture-icon">👤</div>
                <div class="architecture-title">User</div>
            </div>

            <div class="architecture-arrow">→</div>

            <div class="architecture-card">
                <div class="architecture-icon">🤖</div>
                <div class="architecture-title">OpenRouter LLM</div>
            </div>

            <div class="architecture-arrow">→</div>

            <div class="architecture-card">
                <div class="architecture-icon">🔌</div>
                <div class="architecture-title">MCP Client</div>
            </div>

            <div class="architecture-arrow">→</div>

            <div class="architecture-card">
                <div class="architecture-icon">⚙️</div>
                <div class="architecture-title">MCP Server</div>
            </div>

            <div class="architecture-arrow">→</div>

            <div class="architecture-card">
                <div class="architecture-icon">🛠️</div>
                <div class="architecture-title">Tools</div>
            </div>

        </div>
    </div>
    """
)


md('<div class="section-title">MCP Tools</div>')

md(
    """
    <div class="tool-grid">

        <div class="tool-card">
            <div class="tool-icon">🧮</div>
            <div class="tool-name">calculator</div>
            <div class="tool-description">
                Performs mathematical calculations through an MCP tool
                exposed by the Python server.
            </div>
        </div>

        <div class="tool-card">
            <div class="tool-icon">🌐</div>
            <div class="tool-name">tavily_search</div>
            <div class="tool-description">
                Searches the web through Tavily and provides relevant
                information back to the LLM.
            </div>
        </div>

    </div>
    """
)


md('<div class="chat-section">')

# md(
#     """
#     <div class="chat-header">
#         <div class="chat-title">AI Tool Playground</div>
#         <div class="model-badge">OPENROUTER / AUTO</div>
#     </div>
#     """
# )


if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("tools"):
            for tool in message["tools"]:
                render_tool_call(tool)


user_message = st.chat_input(
    "Ask the AI to calculate, search the web, or explain something..."
)


if user_message:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        with st.spinner("LLM deciding which tool to use..."):
            try:
                result = asyncio.run(process_query(user_message))

                st.markdown(result["answer"])

                if result["tools"]:
                    for tool in result["tools"]:
                        render_tool_call(tool, expanded=True)

            except Exception as error:
                result = {
                    "answer": f"Something went wrong: {describe_error(error)}",
                    "tools": [],
                }

                st.error(result["answer"])
                with st.expander("Full traceback (debug)"):
                    st.code(traceback.format_exc())

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "tools": result["tools"],
        }
    )


md("</div>")


md(
    """
    <div class="footer">
        Model Context Protocol · Python MCP SDK · OpenRouter · Tavily
    </div>
    """
)

md("</div>")