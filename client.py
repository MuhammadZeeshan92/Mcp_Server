import json
import os
import sys

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from mcp.types import TextContent
from openai import OpenAI

load_dotenv()

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

if not openrouter_api_key:
    raise ValueError("OPENROUTER_API_KEY is not set in the .env file")

llm = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key,
)

MODEL = "openrouter/auto"


def convert_mcp_tools_to_openai_tools(mcp_tools):
    tools = []

    for tool in mcp_tools:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
        )

    return tools


def extract_tool_result(result):
    output = []

    for block in result.content:
        if isinstance(block, TextContent):
            output.append(block.text)

    return "\n".join(output)


async def process_query(user_message):
    server_path = os.path.join(os.path.dirname(__file__), "server.py")

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[server_path],
    )

    async with Client(server_parameters) as mcp_client:
        tools_result = await mcp_client.list_tools()

        openai_tools = convert_mcp_tools_to_openai_tools(
            tools_result.tools
        )

        messages = [
            {
                "role": "user",
                "content": user_message,
            }
        ]

        tool_activity = []

        while True:
            response = llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                            for tool_call in assistant_message.tool_calls
                        ],
                    }
                )

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    result = await mcp_client.call_tool(
                        tool_name,
                        arguments,
                    )

                    tool_output = extract_tool_result(result)

                    tool_activity.append(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": tool_output,
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_output,
                        }
                    )

                continue

            return {
                "answer": assistant_message.content,
                "tools": tool_activity,
                "available_tools": [
                    {
                        "name": tool.name,
                        "description": tool.description or "",
                    }
                    for tool in tools_result.tools
                ],
            }


async def main():
    user_message = input("Ask something: ")

    result = await process_query(user_message)

    print("\nFinal LLM response:")
    print(result["answer"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())