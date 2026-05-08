import asyncio
import json
import os
import sys
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from groq import AsyncGroq
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

ROOT = str(Path(__file__).resolve().parents[1])

st.set_page_config(page_title="Precificação MEI - Groq", page_icon="💰")
st.title("💰 Assistente de Precificação — Groq")
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
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

for msg in st.session_state.messages:
    if msg["role"] in ("user", "assistant") and "content" in msg:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg.get("tool_usada"):
            st.caption(f" Tool utilizada: `{msg['tool_usada']}`")


CAMPOS_VALIDOS_API = {"role", "content", "name", "tool_call_id", "tool_calls"}

def mensagens_para_api(messages: list) -> list:
    """Remove campos de display (ex: tool_usada) antes de enviar à API."""
    return [{k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API} for msg in messages]


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

                    groq_tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema
                            }
                        }
                        for tool in tools_response.tools
                    ]

                    groq_client = AsyncGroq()
                    tool_usada = None

                    status_box.info("🧠 Consultando o Groq (llama-3.3-70b)...")
                    response = await groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=mensagens_para_api(st.session_state.messages),
                        tools=groq_tools
                    )

                    message = response.choices[0].message
                    st.session_state.messages.append(
                        message.model_dump(exclude_none=True)
                    )

                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            tool_usada = tool_name

                            status_box.warning(f"⚙️ Executando: `{tool_name}`...")
                            print(f"[MCP] tool chamada: {tool_name} | args: {tool_args}", flush=True)

                            result = await session.call_tool(tool_name, tool_args)
                            print(f"[DEBUG] result.content = {result.content}", flush=True)
                            print(f"[DEBUG] type = {type(result.content[0]) if result.content else 'vazio'}", flush=True)

                            try:
                                if result.content:
                                    raw = result.content[0]
                                    result_text = raw.text if hasattr(raw, "text") else str(raw)
                                    result_text = result_text.strip()
                                    result_dict = json.loads(result_text) if result_text else {}
                                else:
                                    result_dict = {}
                            except (json.JSONDecodeError, AttributeError, IndexError) as parse_err:
                                print(f"[AVISO] Erro ao parsear resultado MCP: {parse_err} | raw: {result_text!r}", flush=True)
                                result_dict = {"raw_result": result_text}

                            print(f"[MCP] resultado: {result_dict}", flush=True)

                            st.session_state.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(result_dict, ensure_ascii=False)
                            })

                        status_box.info("Dados recebidos! Gerando resposta final...")

                        final_response = await groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=mensagens_para_api(st.session_state.messages)
                        )

                        resposta_final = final_response.choices[0].message.content

                    else:
                        resposta_final = message.content

                    status_box.empty()
                    st.markdown(resposta_final)

                    if tool_usada:
                        st.caption(f" Tool utilizada: `{tool_usada}`")

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