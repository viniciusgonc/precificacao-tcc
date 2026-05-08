import asyncio
import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from dotenv import load_dotenv
from groq import AsyncGroq
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession

load_dotenv()

ROOT = str(Path(__file__).resolve().parents[1])

SYSTEM_PROMPT = """
Você é um assistente especializado em ajudar microempreendedores individuais (MEIs)
e microempresas (MEs) brasileiros a precificar corretamente seus produtos e serviços.

Seu papel é:
- Explicar termos técnicos (markup, despesas fixas, variáveis) em linguagem simples
- Guiar o empreendedor para coletar as informações necessárias ao cálculo
- Usar as tools disponíveis para garantir que os cálculos sejam sempre precisas
- Após o cálculo, explicar o resultado de forma clara e prática

Nunca invente ou estime valores numéricos — sempre use as tools para calcular.
Responda sempre em português do Brasil.
"""

_GEMINI_CLIENT: Optional[Any] = None


@dataclass
class LLMProvider:
    key: str
    label: str
    description: str
    query_fn: Callable[[str, List[Dict[str, Any]]], Awaitable[Dict[str, Any]]]


def listar_ias() -> List[Dict[str, str]]:
    return [
        {"key": provider.key, "label": provider.label, "description": provider.description}
        for provider in PROVIDERS
    ]


def provider_por_chave(key: str) -> LLMProvider:
    for provider in PROVIDERS:
        if provider.key == key:
            return provider
    raise ValueError(f"Provedor desconhecido: {key}")


def _import_gemini_client() -> Any:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        genai = importlib.import_module("google.genai")
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _GEMINI_CLIENT


def _import_gemini_types() -> Any:
    google_genai = importlib.import_module("google.genai")
    return google_genai.types


async def criar_sessao_mcp() -> ClientSession:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(ROOT, "server.py")]
    )
    client = await stdio_client(server_params).__aenter__()
    read, write = client
    session = await ClientSession(read, write).__aenter__()
    await session.initialize()
    return session


async def executar_tool(session: ClientSession, tool_name: str, tool_args: dict) -> dict:
    result = await session.call_tool(tool_name, tool_args)
    if result.content:
        raw = result.content[0]
        result_text = raw.text if hasattr(raw, "text") else str(raw)
        result_text = result_text.strip()
        try:
            return json.loads(result_text) if result_text else {}
        except json.JSONDecodeError:
            return {"raw_result": result_text}
    return {}


def converter_tools_para_groq(tools_mcp: list) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools_mcp
    ]


def converter_tools_para_gemini(tools_mcp: list) -> list:
    types = _import_gemini_types()
    declarations = []
    for tool in tools_mcp:
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
            )
        )
    return [types.Tool(function_declarations=declarations)]


def reconstruir_historico_gemini(messages: List[Dict[str, Any]]) -> List[Any]:
    types = _import_gemini_types()
    historico = []
    for msg in messages:
        if msg["role"] == "tool":
            continue
        role = "user" if msg["role"] == "user" else "model"
        historico.append(
            types.Content(role=role, parts=[types.Part(text=msg["content"])])
        )
    return historico


def filtrar_mensagens_para_api(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    campos_validos = {"role", "content", "name", "tool_call_id", "tool_calls"}
    return [{k: v for k, v in msg.items() if k in campos_validos} for msg in messages]


async def obter_tools_mcp(session: ClientSession):
    tools_response = await session.list_tools()
    return tools_response.tools


async def query_groq(prompt: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[os.path.join(ROOT, "server.py")])) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_mcp = await obter_tools_mcp(session)
            groq_tools = converter_tools_para_groq(tools_mcp)

            updated_messages = messages + [{"role": "user", "content": prompt}]
            groq_client = AsyncGroq()

            response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=filtrar_mensagens_para_api(updated_messages),
                tools=groq_tools,
            )

            message = response.choices[0].message
            updated_messages.append(message.model_dump(exclude_none=True))
            tool_used = None

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_used = tool_name
                    tool_result = await executar_tool(session, tool_name, tool_args)
                    updated_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    })

                final_response = await groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=filtrar_mensagens_para_api(updated_messages),
                )
                final_text = final_response.choices[0].message.content
                updated_messages.append({"role": "assistant", "content": final_text})
            else:
                final_text = message.content

            return {
                "final_text": final_text,
                "tool_used": tool_used,
                "messages": updated_messages,
            }


async def query_gemini(prompt: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    async with stdio_client(StdioServerParameters(command=sys.executable, args=[os.path.join(ROOT, "server.py")])) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_mcp = await obter_tools_mcp(session)
            gemini_tools = converter_tools_para_gemini(tools_mcp)

            updated_messages = messages + [{"role": "user", "content": prompt}]
            historico = reconstruir_historico_gemini(updated_messages)

            gemini_client = _import_gemini_client()
            types = _import_gemini_types()
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=historico,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=gemini_tools,
                ),
            )

            tool_used = None
            while True:
                part = response.candidates[0].content.parts[0]
                if not hasattr(part, "function_call") or part.function_call is None or not part.function_call.name:
                    break

                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)
                tool_used = tool_name
                tool_result = await executar_tool(session, tool_name, tool_args)

                updated_messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

                historico.append(response.candidates[0].content)
                historico.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name=tool_name,
                                    response={"result": tool_result},
                                )
                            )
                        ],
                    )
                )

                response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=historico,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=gemini_tools,
                    ),
                )

            final_text = response.text
            updated_messages.append({"role": "assistant", "content": final_text})

            return {
                "final_text": final_text,
                "tool_used": tool_used,
                "messages": updated_messages,
            }


PROVIDERS: List[LLMProvider] = [
    LLMProvider(
        key="groq",
        label="Groq",
        description="Use Groq com suporte a ferramentas MCP.",
        query_fn=query_groq,
    ),
]

try:
    importlib.import_module("google.genai")
    PROVIDERS.append(
        LLMProvider(
            key="gemini",
            label="Gemini",
            description="Use Gemini com suporte a ferramentas MCP.",
            query_fn=query_gemini,
        )
    )
except ModuleNotFoundError:
    pass
