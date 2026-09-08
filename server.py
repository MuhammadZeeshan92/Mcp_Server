import ast
import operator
import os
import logging

from dotenv import load_dotenv
from tavily import TavilyClient
from mcp.server import MCPServer

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = MCPServer("Web Search MCP Server")

tavily_api_key = os.getenv("TAVILY_API_KEY")

if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY is not set in the .env file")

tavily_client = TavilyClient(api_key=tavily_api_key)

operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def evaluate_expression(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in operators:
        left = evaluate_expression(node.left)
        right = evaluate_expression(node.right)
        return operators[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate_expression(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value

    raise ValueError("Invalid mathematical expression")


@mcp.tool()
def calculator(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = evaluate_expression(tree.body)
        return str(result)
    except Exception as error:
        return f"Calculation error: {error}"


@mcp.tool()
def tavily_search(query: str) -> str:
    """Search the web using Tavily and return concise relevant results."""
    try:
        response = tavily_client.search(
            query=query,
            search_depth="basic",
            topic="general",
            max_results=5,
            include_answer=True,
        )

        answer = response.get("answer", "")
        results = response.get("results", [])

        output = []

        if answer:
            output.append(f"Answer:\n{answer}")

        if results:
            output.append("\nRelevant sources:")

        for index, result in enumerate(results, start=1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")

            if len(content) > 500:
                content = content[:500] + "..."

            output.append(
                f"\n{index}. {title}\n"
                f"URL: {url}\n"
                f"{content}"
            )

        return "\n".join(output)

    except Exception as error:
        logger.exception("Tavily search failed")
        return f"Search error: {error}"


if __name__ == "__main__":
    mcp.run()