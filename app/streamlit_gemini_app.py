import asyncio
import json
import os
import sys
import time
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

# Inicialização segura do cliente Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ROOT = str(Path(__file__).resolve().parents[1])

st.set_page_config(
    page_title="Precificação MEI - Gemini",
    page_icon="💰",
    layout="centered",
)

# ── CONFIGURAÇÕES DE TEMA NA SIDEBAR ──────────────────────────────────────────
st.sidebar.title("🎨 Customização da Interface")

# Escolha do modo de exibição
modo_tela = st.sidebar.radio("Modo de Exibição", ["Claro", "Escuro"], index=0)

# Pequena paleta conceitual de cores para os balões do usuário e ferramentas
paletas_cores = {
    "Roxo Real": {"primary": "#8B5CF6", "hover": "#7C3AED", "text": "#FFFFFF"},
    "Azul Clássico": {"primary": "#3B82F6", "hover": "#2563EB", "text": "#FFFFFF"},
    "Verde Esmeralda": {"primary": "#10B981", "hover": "#059669", "text": "#FFFFFF"},
    "Rosa Coral": {"primary": "#F43F5E", "hover": "#E11D48", "text": "#FFFFFF"}
}

cor_selecionada = st.sidebar.selectbox("Cor de Destaque (Interface)", list(paletas_cores.keys()))
ui_cor = paletas_cores[cor_selecionada]

# Definição das variáveis CSS baseadas no modo de exibição selecionado
if modo_tela == "Claro":
    css_bg_app = "#F3F4F6"
    css_bg_chat_bot = "#FFFFFF"
    css_text_bot = "#1F2937"
    css_border = "#E5E7EB"
    css_sidebar = "#FFFFFF"
else:
    css_bg_app = "#111827"
    css_bg_chat_bot = "#1F2937"
    css_text_bot = "#F9FAFB"
    css_border = "#374151"
    css_sidebar = "#1F2937"

# ── CUSTOM CSS DINÂMICO INJETADO ──────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
}}

/* Cor de fundo da aplicação */
.stApp {{
    background-color: {css_bg_app};
}}

/* Oculta os menus e headers nativos que conflitam com nossa customização */
[data-testid="stHeader"] {{
    background: transparent;
}}

/* Estilização da Sidebar */
[data-testid="stSidebar"] {{
    background-color: {css_sidebar} !important;
    border-right: 1px solid {css_border};
}}

/* Customização geral dos balões do Streamlit */
[data-testid="stChatMessage"] {{
    border-radius: 16px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    border: 1px solid {css_border};
}}

/* Mudança dinâmica das caixas de mensagem do Usuário com a cor escolhida */
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) {{
    background-color: {ui_cor['primary']} !important;
    color: {ui_cor['text']} !important;
    border: none;
}}

[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) p,
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) li,
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) strong {{
    color: {ui_cor['text']} !important;
}}

[data-testid="stChatMessage"]:has([data-testid="assistant-avatar"]) {{
    background-color: {css_bg_chat_bot} !important;
    color: {css_text_bot} !important;
}}

/* customização das abinhas retráteis (Expanders) de Tools sincronizados com a cor */
.stExpander {{
    background-color: {css_bg_chat_bot} !important;
    border: 1px solid {ui_cor['primary']} !important;
    border-radius: 10px !important;
    margin-top: 6px;
}}

.stExpander summary {{
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
    color: {ui_cor['primary']} !important;
    font-weight: 500;
}}

/* Status info boxes de carregamento sutil */
.status-box {{
    background: {css_bg_chat_bot};
    border-left: 3px solid {ui_cor['primary']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: {css_text_bot};
    margin: 4px 0;
}}
</style>
""", unsafe_allow_html=True)


SYSTEM_PROMPT = """
Você é um assistente de precificação especializado em ajudar microempreendedores
individuais (MEIs) e microempresas (MEs) brasileiros. Você combina conhecimento
técnico com escuta activa — antes de qualquer cálculo, você entende quem é o
empreendedor, o que ele vende e qual é a realidade do negócio dele.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEU JEITO DE ATENDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Você não é um formulário. Você é um consultor acessível que conversa de forma
natural, faz perguntas com propósito e explica o porquê de cada informação que
pede. Seu tom é próximo, claro e sem jargão desnecessário.

NUNCA assuma valores padrão (como 0% ou valores omitidos) para despesas fixas ou 
variáveis se o usuário ainda não os tiver fornecido. Chutar ou ignorar esses custos 
quebra a precisão do Markup e induz o microempreendedor ao prejuízo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOLO DE TRIAGEM OBRIGATÓRIO (PASSO A PASSO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Para evitar erros de cálculo e diagnósticos falsos, você deve seguir RIGOROSAMENTE 
a ordem cronológica de coleta de dados abaixo. NUNCA pule etapas e NUNCA acione 
ferramentas de simulação ou cálculo de preço antes de concluir a triagem de custos estruturais.

FASE 1: Identificação do Produto e Custos Diretos (R$)
  • Entenda o que é o produto/serviço e se a produção ocorre em LOTE (quantidade) ou é um PRODUTO ÚNICO/SERVIÇO SOB MEDIDA.
  • Colete o custo direto em reais (insumos, ingredientes, matéria-prima). Se for lote, peça o custo total gasto e a quantidade produzida.
  • EXPLIQUE AO MEI: "Precisamos começar mapeando o custo bruto dos materiais do seu produto. Essa é a nossa linha de base, ou seja, o valor mínimo que você gasta em dinheiro só para fazer o item existir."

FASE 2: Triagem de Despesas Variáveis (%)
  • Questione ativamente sobre taxas de maquininha de cartão de crédito/débito, comissões de marketplaces (como Shopee, Mercado Livre, iFood) ou impostos diretos por venda.
  • Se o usuário relatar taxas percentuais picadas, use obrigatoriamente a ferramenta `consolidar_despesas_variaveis` para somá-las.
  • EXPLIQUE AO MEI: "Essas taxas saem de forma invisível de cada venda que você faz. Se não descobrirmos o percentual exato delas agora, os intermediários financeiros e as plataformas vão engolir o seu lucro sem você perceber."
  • REGRA: Só avance se o usuário fornecer as taxas ou confirmar explicitamente que a operação não possui nenhuma despesa variável percentual.

FASE 3: Triagem de Despesas Fixas Estruturais (R$ para %)
  • Pergunte sobre os custos fixos mensais nominais da estrutura (aluguel, conta de luz, água, internet, contador, taxa do DAS-MEI) E qual é o Faturamento Mensal Geral (estimado ou real) da empresa inteira.
  • Acione obrigatoriamente a ferramenta `converter_custo_fixo_para_percentual` para traduzir esses valores em reais no peso percentual que o Markup exige.
  • EXPLIQUE AO MEI: "Mesmo que você não venda nada, as contas de aluguel, água e luz vencem todo mês. Precisamos descobrir qual pequena fatia sutil de cada produto vendido vai ajudar a pagar a estrutura física do seu negócio para manter as portas abertas."
  • REGRA: NUNCA pule a coleta de despesas fixas fingindo que elas não existem. Se o negócio é de home-office e não tem custo nenhum, confirme essa condição antes de avançar.

FASE 4: Validação de Segurança e Definição do Lucro
  • Antes de disparar qualquer simulação ou preço final, você DEVE chamar a ferramenta `validar_percentuais` passando os dados percentuais consolidados nas fases anteriores.
  • Se o retorno apontar 'valido': True, pergunte qual a margem de lucro líquido desejada pelo MEI (ex: 25%) ou ofereça a ferramenta `simular_cenarios_de_lucro`.
  • EXPLIQUE AO MEI: "Agora que protegemos seu preço contra as taxas e os custos fixos, vamos definir o Lucro Pretendido — que é o dinheiro que de fato vai sobrar limpo no seu bolso para você reinvestir ou usar como quiser."
  • Se o retorno apontar 'valido': False, pare o fluxo imediatamente e explique o erro matemático conforme as diretrizes da ferramenta.

FASE 5: Execução do Cálculo Final e Viabilidade Comercial
  • Use `calcular_preco_unitario` (para produções em lote) ou `calcular_produto_unico` (para itens ou serviços individuais) para dar o veredito do preço de venda ideal.
  • Dispare AUTOMATICAMENTE a ferramenta `calcular_ponto_de_equilibrio` para fechar a consultoria entregando a meta de vendas mensais necessárias para pagar a estrutura.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AS FERRAMENTAS DE CÁLCULO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Você tem acesso a ferramentas de cálculo precisas e seguras:
  • consolidar_despesas_variaveis        → soma múltiplas taxas percentuais de intermediação.
  • converter_custo_fixo_para_percentual → transforma custos estruturais em reais em percentual rateado.
  • validar_percentuais                  → impede matematicamente erros de divisão por zero ou markup negativo.
  • simular_cenarios_de_lucro            → projeta preços em três perfis comerciais (15%, 25% e 40%).
  • calcular_preco_unitario              → gera o preço de venda recomendado para produções em lote.
  • calcular_produto_unico               → gera o preço de venda recomendado para itens/serviços individuais.
  • calcular_ponto_de_equilibrio         → define a meta física de vendas para o negócio não ter prejuízo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS CRÍTICAS DE CHAMADA DE TOOLS (NUNCA ERRE AQUI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. FORMATO DOS PERCENTUAIS (%): Todos os parâmetros de percentual (como despesas_variaveis, despesas_fixas, lucro_pretendido, taxa_maquininha_cartao, etc.) devem ser informados como números inteiros ou decimais base 100, e NUNCA como frações decimais de 0 a 1.
     - EXEMPLO CORRETO: 25% deve ser enviado como 25.0. 5% deve ser enviado como 5.0. 11% deve ser enviado como 11.0.
     - EXEMPLO ERRADO: NUNCA envie 0.25 para representar 25%, NUNCA envie 0.05 para 5%, NUNCA envie 0.11 para 11%.
  2. SINTAXE PROIBIDA NO TEXTO CORRIDO: NUNCA insira ou escreva por extenso no corpo das suas mensagens marcas de texto como "<function=...>" ou "</function>". A ativação de ferramentas deve ser feita de forma puramente nativa pelo sistema de chamadas ocultas da API (tool_calls).
  3. TIPAGEM E ASPAS: Todos os parâmetros numéricos devem ser passados estritamente como números puros (ex: 10.0, 5.0, 25.0). NUNCA coloque números entre aspas (ex: "10.0", "5").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS GERAIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Responda sempre em português do Brasil.
  • Nunca invente, deduza ou estime valores numéricos de cabeça — use sempre as ferramentas para computar os dados.
  • Use linguagem acessível — o seu público-alvo é composto por trabalhadores autônomos e pequenos empreendedores, não contadores ou acadêmicos.
"""

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 💰 Assistente de Precificação — Gemini")
st.caption("Converse naturalmente sobre como precificar seus produtos e serviços.")
st.divider()

# ── Session state ───────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Helpers ─────────────────────────────────────────────────────────────────────
def deve_exibir(msg: dict) -> bool:
    if msg["role"] not in ("user", "assistant"):
        return False
    conteudo = msg.get("content")
    if not conteudo or not str(conteudo).strip():
        return False
    return True

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
        if msg["role"] == "system":
            continue
        role = "user" if msg["role"] == "user" else "model"
        historico.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )
    return historico

# Função para simular o efeito de máquina de escrever protegida contra nulos
def simular_streaming_texto(texto: str):
    if not texto:
        return
    placeholder = st.empty()
    texto_acumulado = ""
    for palavra in texto.split(" "):
        texto_acumulado += palavra + " "
        placeholder.markdown(texto_acumulado + "▌")
        time.sleep(0.015)
    placeholder.markdown(texto_acumulado)

# ── Render histórico de conversas ───────────────────────────────────────────────
for msg in st.session_state.messages:
    if not deve_exibir(msg):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    if msg.get("tool_usada"):
        with st.expander(f"⚙️ Tool utilizada: `{msg['tool_usada']}`", expanded=False):
            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata pelo Gemini.")

# ── Query / Fluxo do Agente de IA (Gemini) ──────────────────────────────────────
async def query_agent(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_box = st.empty()
        status_box.markdown('<div class="status-box">🔌 Sincronizando ferramentas de precificação…</div>', unsafe_allow_html=True)

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(ROOT, "server.py")]
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    status_box.markdown('<div class="status-box">🛠️ Obtendo ferramentas estruturais…</div>', unsafe_allow_html=True)
                    tools_response = await session.list_tools()
                    declarations = converter_tools_para_gemini(tools_response.tools)
                    gemini_tools = [types.Tool(function_declarations=declarations)]

                    historico = reconstruir_historico(st.session_state.messages[:-1])
                    historico.append(
                        types.Content(role="user", parts=[types.Part(text=prompt)])
                    )

                    status_box.markdown('<div class="status-box">🧠 Consultando inteligência de negócios…</div>', unsafe_allow_html=True)

                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=historico,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=gemini_tools
                        )
                    )

                    tool_usada = None

                    # Loop de chamadas de ferramentas (Tool Calls) do Gemini
                    while True:
                        if not response.candidates or not response.candidates[0].content.parts:
                            break
                        
                        part = response.candidates[0].content.parts[0]

                        if not hasattr(part, "function_call") or part.function_call is None or not part.function_call.name:
                            break

                        tool_name = part.function_call.name
                        tool_args = dict(part.function_call.args)
                        tool_usada = tool_name

                        status_box.markdown(f'<div class="status-box">⚙️ Executando operação estrutural: `{tool_name}`…</div>', unsafe_allow_html=True)

                        result = await session.call_tool(tool_name, tool_args)
                        
                        try:
                            if result.content:
                                raw = result.content[0]
                                result_text = raw.text if hasattr(raw, "text") else str(raw)
                                result_dict = json.loads(result_text.strip()) if result_text.strip() else {}
                            else:
                                result_dict = {}
                        except (json.JSONDecodeError, AttributeError, IndexError):
                            result_dict = {"raw_result": str(result.content)}

                        historico.append(response.candidates[0].content)
                        historico.append(
                            types.Content(
                                role="user",
                                parts=[types.Part(
                                    function_response=types.FunctionResponse(
                                        name=tool_name,
                                        response=result_dict  # CORREÇÃO AQUI: Passado diretamente sem envelopar em {"result": ...}
                                    )
                                )]
                            )
                        )

                        status_box.markdown('<div class="status-box">🧠 Reavaliando cenários integrados…</div>', unsafe_allow_html=True)
                        response = client.models.generate_content(
                            model="gemini-2.5-flash-lite",
                            contents=historico,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                tools=gemini_tools
                            )
                        )

                    # Captura de resposta de forma robusta
                    resposta_final = response.text if response.text else ""
                    if not resposta_final and response.candidates and response.candidates[0].content.parts:
                        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, "text") and p.text]
                        resposta_final = "".join(text_parts)

                    status_box.empty()
                    
                    if resposta_final:
                        simular_streaming_texto(resposta_final)
                    else:
                        resposta_final = "Cálculo processado com sucesso. Como posso te ajudar a detalhar o preço agora?"
                        st.markdown(resposta_final)

                    if tool_usada:
                        with st.expander(f"⚙️ Tool utilizada: `{tool_usada}`", expanded=False):
                            st.caption("Esta ferramenta MCP foi disparada com sucesso para computar os dados de forma exata pelo Gemini.")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada
                    })

        except Exception as e:
            import traceback
            status_box.error(f"Ocorreu uma inconsistência no processamento: {str(e)}")
            st.code(traceback.format_exc(), language="text")

if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))