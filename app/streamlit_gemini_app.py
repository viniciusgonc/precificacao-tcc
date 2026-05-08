import asyncio
import json
import os
import sys
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ROOT = str(Path(__file__).resolve().parents[1])

st.set_page_config(page_title="Precificação MEI - Gemini", page_icon="💰")
st.title("💰 Assistente de Precificação — Gemini")
st.write("Converse naturalmente sobre como precificar seus produtos e serviços.")

SYSTEM_PROMPT = """
Você é um assistente especializado em ajudar microempreendedores individuais (MEIs)
e microempresas (MEs) brasileiros a precificar corretamente seus produtos e serviços.

Seu papel é:
- Explicar termos técnicos (markup, despesas fixas, variáveis) em linguagem simples
- Guiar o empreendedor para coletar as informações necessárias ao cálculo
- Usar as tools disponíveis para garantir que os cálculos sejam sempre precisos
- Após o cálculo, explicar o resultado de forma clara e prática

Nunca invente ou estime valores numéricos — sempre use as tools para calcular.
Responda sempre em português do Brasil.
"""

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] in ("user", "assistant") and "content" in msg:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg.get("tool_usada"):
            st.caption(f"🔧 Tool utilizada: `{msg['tool_usada']}`")


def converter_tools_para_gemini(tools_mcp: list) -> list:
    declarations = []
    for tool in tools_mcp:
        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema
            )
        )
    return declarations


def reconstruir_historico(messages: list) -> list:
    historico = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        historico.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )
    return historico


async def query_agent(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_box = st.empty()
        status_box.info("🔌 Conectando ao servidor MCP...")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(ROOT, "server.py")]
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    status_box.info("🛠️ Obtendo ferramentas de precificação...")
                    tools_response = await session.list_tools()
                    declarations = converter_tools_para_gemini(tools_response.tools)
                    gemini_tools = [types.Tool(function_declarations=declarations)]

                    historico = reconstruir_historico(st.session_state.messages[:-1])
                    historico.append(
                        types.Content(role="user", parts=[types.Part(text=prompt)])
                    )

                    status_box.info("🧠 Consultando o Gemini...")

                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=historico,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=gemini_tools
                        )
                    )

                    tool_usada = None

                    # Loop de tool calls
                    while True:
                        part = response.candidates[0].content.parts[0]

                        if not hasattr(part, "function_call") or part.function_call is None or not part.function_call.name:
                            break

                        tool_name = part.function_call.name
                        tool_args = dict(part.function_call.args)
                        tool_usada = tool_name

                        status_box.warning(f"⚙️ Executando: `{tool_name}`...")
                        print(f"🔧 [MCP] tool chamada: {tool_name} | args: {tool_args}", flush=True)

                        result = await session.call_tool(tool_name, tool_args)
                        print(f"🔍 [DEBUG] result.content = {result.content}", flush=True)
                        print(f"🔍 [DEBUG] type = {type(result.content[0]) if result.content else 'vazio'}", flush=True)
                        try:
                            if result.content:
                                raw = result.content[0]
                                result_text = raw.text if hasattr(raw, "text") else str(raw)
                                result_text = result_text.strip()
                                result_dict = json.loads(result_text) if result_text else {}
                            else:
                                result_dict = {}
                        except (json.JSONDecodeError, AttributeError, IndexError) as parse_err:
                            print(f"⚠️ Erro ao parsear resultado MCP: {parse_err} | raw: {result_text!r}", flush=True)
                            result_dict = {"raw_result": result_text}

                        print(f"✅ [MCP] resultado: {result_dict}", flush=True)

                        historico.append(response.candidates[0].content)
                        historico.append(
                            types.Content(
                                role="user",
                                parts=[types.Part(
                                    function_response=types.FunctionResponse(
                                        name=tool_name,
                                        response={"result": result_dict}
                                    )
                                )]
                            )
                        )

                        response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=historico,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                tools=gemini_tools
                            )
                        )

                    resposta_final = response.text
                    status_box.empty()
                    st.markdown(resposta_final)

                    if tool_usada:
                        st.caption(f"🔧 Tool utilizada: `{tool_usada}`")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada
                    })

        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            status_box.error(f"Erro: {str(e)}")
            st.code(erro_completo, language="text")
            print(erro_completo, flush=True)


if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))