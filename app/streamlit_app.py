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


st.set_page_config(
    page_title="Precificação MEI",
    page_icon="💰",
    layout="centered",
)


# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');


html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}


/* Page background */
.stApp {
    background-color: #f7f8fa;
}


/* Top header area */
[data-testid="stHeader"] {
    background: transparent;
}


/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e8eaed;
}


/* Chat messages */
[data-testid="stChatMessage"] {
    background-color: #ffffff;
    border: 1px solid #e8eaed;
    border-radius: 12px;
    padding: 4px 8px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}


/* Chat input */
[data-testid="stChatInput"] textarea {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    font-family: 'DM Sans', sans-serif;
}


/* Tool badge */
.tool-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #15803d;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    margin-top: 4px;
}


/* Status info boxes */
.status-box {
    background: #eff6ff;
    border-left: 3px solid #3b82f6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #1e40af;
    margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)


SYSTEM_PROMPT = """
Você é um assistente de precificação especializado em ajudar microempreendedores
individuais (MEIs) e microempresas (MEs) brasileiros. Você combina conhecimento
técnico com escuta ativa — antes de qualquer cálculo, você entende quem é o
empreendedor, o que ele vende e qual é a realidade do negócio dele.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEU JEITO DE ATENDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Você não é um formulário. Você é um consultor acessível que conversa de forma
natural, faz perguntas com propósito e explica o porquê de cada informação que
pede. Seu tom é próximo, claro e sem jargão desnecessário.


Sempre que o usuário chegar com uma dúvida ou quiser calcular o preço de algo,
siga esta lógica de conversa:


  1. ENTENDA A SITUAÇÃO
     Antes de pedir números, entenda o contexto do negócio. Pergunte sobre o
     que ele vende, como produz, se trabalha sozinho ou com equipe, se tem loja
     física ou vende online. Essas informações vão guiar toda a conversa e
     tornar suas explicações muito mais relevantes para a realidade dele.


  2. EXPLIQUE O QUE ESTÁ POR TRÁS DO CÁLCULO
     Conforme o usuário compartilha a situação, explique naturalmente por que
     a precificação importa para o negócio DELE. Use exemplos do próprio
     contexto que ele descreveu. Se ele faz bolos, fale de bolos. Se presta
     serviços de manutenção, use esse cenário.


     Conceitos que você pode explicar ao longo da conversa:
     • Markup: o fator que garante que o preço cubra tudo e ainda gere lucro
     • Despesas variáveis: o que muda a cada venda (frete, taxa de cartão, etc.)
     • Despesas fixas: o que é pago todo mês independente de vender ou não
     • Lucro pretendido: o quanto o empreendedor quer de retorno sobre o preço


  3. COLETE OS DADOS COM CONTEXTO
     Peça cada informação explicando por que ela importa. Nunca jogue uma
     lista de campos na tela. Vá um passo de cada vez, naturalmente.


     Para fazer o cálculo de precificação, você vai precisar de:


     Se o produto é feito em LOTE (várias unidades de uma produção):
       • Custo total do lote em reais — "quanto gastou para produzir tudo?"
       • Quantidade de unidades produzidas
       • Despesas variáveis em % — taxas, comissões, frete por venda
       • Despesas fixas em % — aluguel, energia, contador, etc.
       • Lucro pretendido em %


     Se é um produto ÚNICO ou serviço individual:
       • Custo de produção daquele item em reais
       • Despesas variáveis em %
       • Despesas fixas em %
       • Lucro pretendido em %


     Se o usuário não souber como calcular os percentuais de despesas,
     ajude-o a chegar nesses valores com perguntas simples sobre os custos
     mensais e o faturamento estimado.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AS FERRAMENTAS DE CÁLCULO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Você tem acesso a duas ferramentas de cálculo precisas:
  • calcular_preco_unitario → para produtos feitos em lote
  • calcular_produto_unico  → para produtos únicos ou serviços


Essas ferramentas existem para garantir que nenhum cálculo seja feito na
estimativa — os resultados são sempre exatos.


Você SÓ deve chamar uma ferramenta quando:
  ✅ Todos os valores necessários foram fornecidos e confirmados pelo usuário
  ✅ A soma (despesas variáveis + despesas fixas + lucro pretendido) for menor
     que 100% — caso contrário, o cálculo é matematicamente impossível e você
     deve pedir ao usuário que revise os percentuais antes de prosseguir
  ✅ O tipo de produto (lote ou único) está definido


Antes de executar, apresente um resumo dos dados e confirme com o usuário.


Nunca chame as ferramentas para:
  ✗ Responder perguntas conceituais ou explicativas
  ✗ Exemplificar com valores hipotéticos
  ✗ Situações em que os dados ainda estão incompletos


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APÓS O CÁLCULO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Explique o resultado conectando com a realidade que o usuário descreveu.
Mostre o que cada número significa para o negócio dele especificamente.
Aponte se o preço encontrado parece competitivo para o mercado dele, se
há margem para negociação ou se há riscos caso venda abaixo desse valor.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS GERAIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


  • Responda sempre em português do Brasil
  • Nunca invente ou estime valores numéricos — use sempre as ferramentas
  • Use linguagem acessível — o público é empreendedor, não contador
  • Se algo der errado na ferramenta, informe o usuário com clareza e sem
    expor detalhes técnicos do sistema
"""


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 💰 Assistente de Precificação")
st.caption("Converse naturalmente sobre como precificar seus produtos e serviços.")
st.divider()


# ── Session state ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]


# ── Helpers ─────────────────────────────────────────────────────────────────────
CAMPOS_VALIDOS_API = {"role", "content", "name", "tool_call_id", "tool_calls"}




def mensagens_para_api(messages: list) -> list:
    return [{k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API} for msg in messages]




def deve_exibir(msg: dict) -> bool:
    """
    Retorna True apenas para mensagens de usuário e assistente que devem ser
    exibidas no chat. Exclui:
      - Mensagens de sistema
      - Mensagens de ferramenta (role=tool)
      - Mensagens intermediárias do assistente com tool_calls (sem conteúdo útil)
    """
    if msg["role"] not in ("user", "assistant"):
        return False
    # Mensagens com tool_calls são intermediárias — o Groq as usa internamente
    if msg.get("tool_calls"):
        return False
    conteudo = msg.get("content")
    if not conteudo or not str(conteudo).strip():
        return False
    return True




# ── Render histórico ────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if not deve_exibir(msg):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    if msg.get("tool_usada"):
        st.markdown(
            f'<div class="tool-badge">⚙️ {msg["tool_usada"]}</div>',
            unsafe_allow_html=True,
        )




# ── Query ────────────────────────────────────────────────────────────────────────
async def query_agent(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})


    # Exibe a mensagem do usuário imediatamente
    with st.chat_message("user"):
        st.markdown(prompt)


    with st.chat_message("assistant"):
        status_box = st.empty()


        server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(ROOT, "server.py")]
        )


        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()


                    status_box.info("Obtendo ferramentas de precificação…")
                    tools_response = await session.list_tools()


                    groq_tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        }
                        for tool in tools_response.tools
                    ]


                    groq_client = AsyncGroq()
                    tool_usada = None


                    status_box.info("Consultando o modelo…")
                    response = await groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=mensagens_para_api(st.session_state.messages),
                        tools=groq_tools,
                    )


                    message = response.choices[0].message
                    # Salva a mensagem intermediária na memória da API,
                    # mas ela NÃO será exibida pois terá tool_calls
                    st.session_state.messages.append(
                        message.model_dump(exclude_none=True)
                    )


                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            tool_usada = tool_name


                            status_box.info(f"Executando cálculo: `{tool_name}`…")


                            result = await session.call_tool(tool_name, tool_args)


                            try:
                                if result.content:
                                    raw = result.content[0]
                                    result_text = raw.text if hasattr(raw, "text") else str(raw)
                                    result_dict = json.loads(result_text.strip()) if result_text.strip() else {}
                                else:
                                    result_dict = {}
                            except (json.JSONDecodeError, AttributeError, IndexError) as e:
                                result_dict = {"raw_result": str(e)}


                            st.session_state.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(result_dict, ensure_ascii=False),
                            })


                        status_box.info("Gerando resposta final…")
                        final_response = await groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=mensagens_para_api(st.session_state.messages),
                        )
                        resposta_final = final_response.choices[0].message.content
                    else:
                        resposta_final = message.content


                    status_box.empty()
                    st.markdown(resposta_final)


                    if tool_usada:
                        st.markdown(
                            f'<div class="tool-badge">⚙️ {tool_usada}</div>',
                            unsafe_allow_html=True,
                        )


                    # Salva apenas a resposta final limpa no histórico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada,
                    })


        except Exception as e:
            import traceback
            status_box.error(f"Erro: {str(e)}")
            st.code(traceback.format_exc(), language="text")




if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))
