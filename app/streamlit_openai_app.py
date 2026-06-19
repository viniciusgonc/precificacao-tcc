import asyncio
import json
import os
import re
import sys
import time
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
 
load_dotenv()
ROOT = str(Path(__file__).resolve().parents[1])
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════
 
MODEL = "gpt-4o-mini"
 
# Resumo automático: dispara quando o histórico ultrapassa X mensagens de usuário
SUMMARY_TRIGGER_COUNT = 10
# Número de mensagens recentes (user + assistant) preservadas integralmente
SUMMARY_KEEP_RECENT = 6
 
CAMPOS_VALIDOS_API = {"role", "content", "name", "tool_call_id", "tool_calls"}
 
FRASES_SINAL_VERDE = [
    "pode calcular", "calcular agora", "confirmo, pode calcular",
    "confirmo pode calcular", "sim, pode calcular", "pode calcular!",
    "autorizo calcular", "pode rodar", "roda o cálculo", "rodar cálculo",
]
 
TOOLS_CALCULO_FINAL = {
    "calcular_preco_unitario",
    "calcular_produto_unico",
    "calcular_preco_por_margem_contribuicao",
}
 
TOOLS_PONTO_EQUILIBRIO = {"calcular_ponto_de_equilibrio"}
 
FASES_LABELS = [
    "Custos Diretos", "Despesas Variáveis", "Despesas Fixas",
    "Diagnóstico", "Cálculo", "Equilíbrio",
]
 
COLOR_PALETTES = {
    "Âmbar Profissional": {"primary": "#D97706", "hover": "#B45309", "text": "#FFFFFF"},
    "Azul Atlântico":     {"primary": "#0EA5E9", "hover": "#0284C7", "text": "#FFFFFF"},
    "Verde Esmeralda":    {"primary": "#10B981", "hover": "#059669", "text": "#FFFFFF"},
    "Rosa Coral":         {"primary": "#F43F5E", "hover": "#E11D48", "text": "#FFFFFF"},
    "Roxo Real":          {"primary": "#8B5CF6", "hover": "#7C3AED", "text": "#FFFFFF"},
}
 
DADOS_PRECIFICACAO_VAZIO = {
    "custo_unitario": None, "quantidade": None, "tipo_produto": None,
    "despesas_variaveis": None, "custo_fixo_mensal": None,
    "faturamento_mensal": None, "despesas_fixas_pct": None,
    "estrategia": None, "lucro_ou_margem_alvo": None,
    "preco_calculado": None, "contexto_negocio": [],
}
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
 
SYSTEM_PROMPT = """
# ATUAÇÃO DO AGENTE
Você é um consultor de precificação e o **sócio estratégico** para Microempreendedores Individuais (MEIs) brasileiros. Alie o rigor matemático das ferramentas a um atendimento didático, empático, focado em educação financeira e altamente sensível ao contexto do produto ou serviço do usuário. Você enxerga o negócio do usuário como se fosse seu parceiro comercial.
 
## 1. REGRAS CRÍTICAS DE CONDUÇÃO (ANTI-ALUCINAÇÃO)
- PROIBIDO CÁLCULO MANUAL: Você não calcula nada de cabeça. Valores numéricos de preço e ponto de equilíbrio devem vir EXCLUSIVAMENTE do retorno das ferramentas MCP. Nunca deduza valores no texto.
- PROIBIDO PARALELISMO DEPENDENTE: Nunca chame calcular_ponto_de_equilibrio junto com ferramentas de preço no mesmo turno. Aguarde o preço ser gerado no backend pelo Python para, no passo sequencial seguinte do loop, usar o valor exato retornado.
- PROIBIDO CHAMAR TOOLS DE PREÇO ANTES DO SINAL VERDE: As ferramentas calcular_preco_por_margem_contribuicao, calcular_preco_unitario e calcular_produto_unico só podem ser acionadas DEPOIS que o usuário enviar a mensagem de confirmação. Antes disso, apenas apresente o checklist e aguarde.
 
## 2. PROTOCOLO SEQUENCIAL DE TRIAGEM
 
### FASE 1: Insumos e Custos Diretos (R$)
- Identifique se o produto opera em LOTE ou ITEM ÚNICO.
- **Sensibilidade de Sócio:** Demonstre que entende o produto ou serviço do MEI. Adapte seus exemplos e termos ao nicho dele (se vende doces, fale de insumos culinários; se faz quadros/arte, fale de molduras, tintas e tempo de criação).
- **Diferenciação de Volume:** Explique brevemente ao usuário que vender um **produto único** (ex: um serviço exclusivo ou item artesanal principal) exige que ele carregue uma responsabilidade maior sobre a estrutura da empresa, enquanto uma operação de **múltiplos produtos** permite diluir esses percentuais entre diferentes vendas.
- Se for lote, apresente a divisão em reais e confirme o custo unitário bruto de base com o usuário antes de avançar.
- Se houver custos diretos unitários já informados, registre-os como custo unitário de insumos.
 
### FASE 2: Despesas Variáveis (%)
- Identifique taxas de cartões, marketplaces, impostos sobre venda, comissões e outros percentuais.
- Use consolidar_despesas_variaveis se houver taxas picadas.
- Confirme o percentual consolidado com o usuário.
- Custos variáveis in reais (frete fixo por unidade, embalagem) somam ao custo da Fase 1, nunca como percentual.
 
### FASE 3: Despesas Fixas Estruturais (R$ para %)
- Solicite a soma das contas fixas mensais e o faturamento mensal geral da empresa.
- Chame obrigatoriamente converter_custo_fixo_para_percentual. Mostre o resultado em %.
- Reforce o impacto: se o MEI vende múltiplos produtos, esse percentual é o que este produto específico vai "carregar" para ajudar a pagar a estrutura interna.
 
### FASE 4: Diagnóstico, Educação e Coleta de Margem Alvo
- Chame a ferramenta validar_percentuais com os dados coletados.
- **A Pergunta de Filtro Obrigatória:** Você deve abordar o usuário exatamente com esta abordagem:
  *"Agora vamos pensar na margem de contribuição ou lucro pretendido. Você quer calcular por qual parâmetro? Conhece a diferença?"*
 
- **Tratamento do Contexto de Conhecimento:**
    * *Se o usuário já souber a diferença:* Pergunte diretamente qual o percentual que ele deseja aplicar e prossiga para a recomendação de sócio.
    * *Se o usuário NÃO souber ou quiser entender:* Explique as duas abordagens utilizando estritamente os critérios abaixo:
        * **Quando usar Markup (Lucro Pretendido):** Excelente para quem busca agilidade no dia a dia (como revendedores ou lojistas que multiplicam o custo de aquisição rapidamente) ou para quem faz controle de estoque em massa com milhares de produtos parecidos. Ele garante que o preço base pague o custo, mas não garante a rentabilidade final sozinho.
        * **Quando usar Margem de Contribuição (Rentabilidade):** Essencial para vendas em E-commerce e Marketplaces (para calcular o impacto real de taxas e comissões), para quem precisa negociar descontos sabendo o limite antes do prejuízo, ou para quem tem um mix diversificado de produtos e quer descobrir quais trazem mais caixa para pagar as contas fixas.
 
- **A Verdadeira Recomendação de Sócio (Análise de Viabilidade):** Antes de fechar o checklist, cruze os dados da Fase 1 e Fase 3. 
  * Se o usuário produzir **pouquíssimo volume (ex: 1 quadro por mês)** e o custo fixo percentual for muito alto (acima de 30%), alerte-o de que a Margem de Contribuição tradicional em % pode fazer a conta estourar (passar de 100%). 
  * **Recomendação Estratégica:** Nesses cenários de peça única e baixo volume, recomende usar o **Markup** calculando o Preço Base baseado no Custo de Produção + Valor do Custo Fixo absoluto em Reais que aquela peça precisa cobrir, adicionando o Lucro pretendido em cima, para que ele não saia no prejuízo. Os especialistas sugerem usar o markup para chegar ao preço base e depois checar a margem de contribuição para validar se a venda é rentável.
 
- Após o usuário definir e alinhar a estratégia (Margem ou Markup) e o percentual desejado, apresente o checklist abaixo e aguarde.
 
Modelo de checklist:
"Perfeito! Já tenho o diagnóstico estrutural do seu negócio em mãos. Para não darmos um tiro no escuro, vou realizar o cálculo usando estes valores exatos do seu negócio:
- Custo Unitário de Insumos: R$ X,XX
- Taxas e Despesas Variáveis: X,X%
- Custo Fixo (% sobre faturamento): X,X%
- Dinâmica de Venda: [Único Produto / Múltiplos Produtos]
- Estratégia Escolhida: [Margem de Contribuição Alvo de X% ou Markup Tradicional com X% de Lucro]
 
Me confirme se os valores estão corretos e me dê o seu sinal verde (digite 'Pode calcular') para eu rodar o sistema e te entregar o preço ideal de vitrine e a sua meta de vendas!"
 
### FASE 5: Execução Pós-Sinal Verde e Transparência
- Só realize o cálculo após o usuário confirmar com "Pode calcular" ou equivalente.
- Apresente o resultado do Python detalhando cada linha: custo, valor destinado às taxas e margem de contribuição em reais.
 
### FASE 6: Ponto de Equilíbrio
- Dispare calcular_ponto_de_equilibrio de forma isolada usando os valores reais calculados.
- Explique ao usuário quantas unidades ele precisa vender para cobrir os custos fixos mensais com base no cenário dele.
 
## 3. MAPEAMENTO DE PARÂMETROS MCP
- consolidar_despesas_variaveis -> taxa_maquininha_cartao, comissao_marketplace, imposto_sobre_venda, outros_percentuais
- converter_custo_fixo_para_percentual -> custo_fixo_mensal, faturamento_mensal
- validar_percentuais -> despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_preco_unitario -> custo_total, quantidade, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_produto_unico -> custo_producao, despesas_variaveis, despesas_fixas, lucro_pretendido
- calcular_ponto_de_equilibrio -> custos_fixos_mensais, preco_unitario, custo_unitario
- calcular_preco_por_margem_contribuicao -> custo_unitario, despesas_variaveis, margem_contribuicao_alvo
 
## 4. REGRAS DE SINTAXE E SEGURANÇA
- Percentuais sempre na base 100 (ex: 8% = 8.0, NUNCA 0.08).
- Parâmetros numéricos sem aspas (ex: 10.0, 550.0).
- Nunca escreva marcações de ferramenta no texto final, como "<function=...>".
- Nunca invente valores ausentes. Faça perguntas objetivas quando faltar info.
- **Tom de Voz:** Adote uma postura de parceria societária, usando termos acolhedores que incluam você na busca pelo sucesso do negócio (ex: "nossa meta", "nossa margem", "precisamos cobrir").
- Idioma: Português do Brasil.
"""
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════
 
st.set_page_config(
    page_title="Precificação MEI",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="expanded",
)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — INICIALIZAÇÃO DO SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
 
def _init_state():
    """Garante que todas as chaves do session_state existam."""
    defaults = {
        # Histórico COMPLETO — usado apenas para renderização visual na tela.
        # NUNCA é comprimido ou truncado. O usuário sempre vê toda a conversa.
        "messages_display": [{"role": "system", "content": SYSTEM_PROMPT}],
        # Histórico para envio à API — pode ser comprimido pelo resumo automático.
        # Contém system prompt + mensagens (possivelmente resumidas).
        "messages_api":     [{"role": "system", "content": SYSTEM_PROMPT}],
        "fase_protocolo":    1,
        "sinal_verde":       False,
        "dados_precificacao": DADOS_PRECIFICACAO_VAZIO.copy(),
        "session_tokens":    0,
        "resumo_ativo":      False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
 
_init_state()
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 5 — TEMA E CSS DINÂMICO
# ═══════════════════════════════════════════════════════════════════════════════
 
def _build_css(cor: dict) -> str:
    primary = cor["primary"]
    hover = cor["hover"]
    text_on_primary = cor["text"]

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

footer {{
    visibility: hidden !important;
}}

.block-container {{
    padding-top: 7rem !important;
    padding-bottom: 10rem !important;
}}

[data-testid="stChatMessage"] {{
    margin-bottom: 10px !important;
    padding: 14px 18px !important;
    border-radius: 18px !important;
}}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) {{
    background-color: {primary} !important;
    border: 1px solid {primary} !important;
    border-radius: 18px 18px 4px 18px !important;
}}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) *,
[data-testid="stChatMessage"]:has([data-testid="user-avatar"]) * {{
    color: {text_on_primary} !important;
}}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]),
[data-testid="stChatMessage"]:has([data-testid="assistant-avatar"]) {{
    border-radius: 18px 18px 18px 4px !important;
}}

[data-testid="stChatInput"] button {{
    background-color: {primary} !important;
    color: {text_on_primary} !important;
    border-radius: 10px !important;
    border: none !important;
}}

[data-testid="stChatInput"] button:hover {{
    background-color: {hover} !important;
}}

.stButton button {{
    background-color: {primary} !important;
    color: {text_on_primary} !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
}}

.stButton button:hover {{
    background-color: {hover} !important;
}}

.status-box {{
    border-left: 3px solid {primary};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    margin: 4px 0;
    font-family: 'Plus Jakarta Sans', sans-serif;
}}

.token-badge {{
    background: rgba(217, 119, 6, 0.10);
    border: 1px solid rgba(217, 119, 6, 0.35);
    border-radius: 10px;
    padding: 10px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: {primary} !important;
    text-align: center;
    margin-top: 4px;
}}

.token-badge * {{
    color: {primary} !important;
}}

.stExpander summary,
.stExpander summary * {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    color: {primary} !important;
}}

code {{
    color: {primary} !important;
    border-radius: 6px !important;
    padding: 2px 5px !important;
}}
</style>
"""
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
 
def renderizar_progresso_sidebar(container) -> None:
    with container:
        st.markdown("### 📍 Progresso")
        fase_atual = st.session_state.fase_protocolo
        for i, fl in enumerate(FASES_LABELS, start=1):
            if i < fase_atual:
                st.markdown(f"✅ **Fase {i}:** {fl}")
            elif i == fase_atual:
                st.markdown(f"🔵 **Fase {i}: {fl}** ←")
            else:
                st.markdown(f"⬜ Fase {i}: {fl}")


def renderizar_tokens_sidebar(container) -> None:
    with container:
        st.markdown("### 🔢 Uso de Tokens")
        tokens = st.session_state.session_tokens
        st.markdown(
            f'<div class="token-badge">Sessão atual<br/>'
            f'<strong>{tokens:,}</strong> tokens usados</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.resumo_ativo:
            st.caption("🗜️ Resumo automático ativo — contexto da IA comprimido (histórico visual preservado)")
        custo_estimado = tokens * 0.00000037
        st.caption(f"Custo estimado: ~US$ {custo_estimado:.4f}")


def atualizar_sidebar_dinamica() -> None:
    if "progress_placeholder" in st.session_state:
        st.session_state.progress_placeholder.empty()
        renderizar_progresso_sidebar(
            st.session_state.progress_placeholder.container()
        )
    if "tokens_placeholder" in st.session_state:
        st.session_state.tokens_placeholder.empty()
        renderizar_tokens_sidebar(
            st.session_state.tokens_placeholder.container()
        )

with st.sidebar:
    st.markdown("## 💰 Precificação MEI")
    st.caption(f"Modelo: `{MODEL}`")
    st.divider()

    st.markdown("### 🎨 Aparência")
    cor_nome = st.selectbox(
        "Cor de destaque",
        list(COLOR_PALETTES.keys()),
        key="cor_selecionada",
    )
    ui_cor = COLOR_PALETTES[cor_nome]

    st.divider()

    progress_placeholder = st.empty()
    st.session_state.progress_placeholder = progress_placeholder
    renderizar_progresso_sidebar(progress_placeholder.container())

    st.divider()

    tokens_placeholder = st.empty()
    st.session_state.tokens_placeholder = tokens_placeholder
    renderizar_tokens_sidebar(tokens_placeholder.container())
 
    st.divider()
 
    if not os.getenv("OPENAI_API_KEY"):
        api_key = st.text_input("🔑 OpenAI API Key", type="password")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            st.success("Chave registrada nesta sessão.")
    else:
        st.success("✓ API Key carregada do ambiente")
 
    st.divider()
 
    if st.button("🔄 Nova Consulta", use_container_width=True):
        st.session_state.messages_display   = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.messages_api       = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.fase_protocolo     = 1
        st.session_state.sinal_verde        = False
        st.session_state.dados_precificacao = DADOS_PRECIFICACAO_VAZIO.copy()
        st.session_state.resumo_ativo       = False
        st.rerun()
 
 
st.markdown(_build_css(ui_cor), unsafe_allow_html=True)
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 7 — FUNÇÕES AUXILIARES PURAS
# ═══════════════════════════════════════════════════════════════════════════════
 
def deve_exibir(msg: dict) -> bool:
    """True se a mensagem deve aparecer no histórico visual."""
    if msg["role"] not in ("user", "assistant"):
        return False
    if msg.get("tool_calls"):
        return False
    conteudo = msg.get("content")
    return bool(conteudo and str(conteudo).strip())
 
 
def detectar_sinal_verde(texto: str) -> bool:
    normalizado = texto.strip().lower()
    return any(frase in normalizado for frase in FRASES_SINAL_VERDE)
 
 
def atualizar_contexto_negocio(texto: str) -> None:
    keywords = [
        "não vendo só", "não vendo apenas", "também vendo", "outros produtos",
        "loja física", "loja online", "vendo online", "vendo no instagram",
        "vendo no whatsapp", "home office", "sem loja", "autônomo",
    ]
    for kw in keywords:
        if kw in texto.lower():
            obs = texto.strip()
            contexto = st.session_state.dados_precificacao["contexto_negocio"]
            if obs not in contexto:
                contexto.append(obs)
            break
 
 
def limpar_resposta(texto: str) -> str:
    if not texto:
        return texto
    texto = re.sub(r'<function=\w+>\s*\{.*?\}\s*</function>', '', texto, flags=re.DOTALL)
    texto = re.sub(r'<function=\w+>.*', '', texto, flags=re.DOTALL)
    linhas = [linha for linha in texto.splitlines() if linha.strip()]
    return "\n".join(linhas).strip()
 
 
def label_fase(fase: int) -> str:
    labels = {
        1: "Fase 1 — Custos Diretos",
        2: "Fase 2 — Despesas Variáveis",
        3: "Fase 3 — Despesas Fixas",
        4: "Fase 4 — Diagnóstico & Checklist",
        5: "Fase 5 — Cálculo Autorizado",
        6: "Fase 6 — Ponto de Equilíbrio",
    }
    return labels.get(fase, f"Fase {fase}")


def mensagens_para_api(messages: list) -> list:
    """
    Prepara o histórico da API para envio à OpenAI.
    Descarta logs técnicos antigos de tool calls (mais de 2 mensagens de usuário atrás).
    Opera sobre messages_api (já possivelmente resumido), nunca sobre messages_display.
    """
    api_msgs = []
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            api_msgs.append({k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API})
            continue
 
        is_old_tool_log = False
        if msg["role"] == "tool" or (msg["role"] == "assistant" and msg.get("tool_calls")):
            user_msgs_depois = sum(1 for m in messages[i + 1:] if m["role"] == "user")
            if user_msgs_depois >= 2:
                is_old_tool_log = True
 
        if not is_old_tool_log:
            api_msgs.append({k: v for k, v in msg.items() if k in CAMPOS_VALIDOS_API})
 
    return api_msgs
 
 
def sincronizar_estado_tool(tool_name: str, tool_args: dict, result_dict: dict) -> None:
    dados = st.session_state.dados_precificacao
 
    if tool_name == "converter_custo_fixo_para_percentual":
        if "percentual" in result_dict:
            dados["despesas_fixas_pct"] = result_dict["percentual"]
        if "custo_fixo_mensal" in tool_args:
            dados["custo_fixo_mensal"] = tool_args["custo_fixo_mensal"]
        if "faturamento_mensal" in tool_args:
            dados["faturamento_mensal"] = tool_args["faturamento_mensal"]
        if st.session_state.fase_protocolo <= 3:
            st.session_state.fase_protocolo = 4
 
    elif tool_name == "consolidar_despesas_variaveis":
        if "despesas_variaveis_totais" in result_dict:
            dados["despesas_variaveis"] = result_dict["despesas_variaveis_totais"]
        if st.session_state.fase_protocolo <= 2:
            st.session_state.fase_protocolo = 3
 
    elif tool_name == "validar_percentuais":
        if st.session_state.fase_protocolo <= 3:
            st.session_state.fase_protocolo = 4
 
    elif tool_name in TOOLS_CALCULO_FINAL:
        preco = (
            result_dict.get("preco_unitario")
            or result_dict.get("preco_final")
            or result_dict.get("preco_venda")
        )
        if preco:
            dados["preco_calculado"] = preco
        st.session_state.fase_protocolo = 6
 
    elif tool_name == "calcular_ponto_de_equilibrio":
        st.session_state.fase_protocolo = 6
 
 
def simular_streaming_texto(texto: str) -> None:
    if not texto:
        return
    placeholder = st.empty()
    acumulado = ""
    for palavra in texto.split(" "):
        acumulado += palavra + " "
        placeholder.markdown(acumulado + "▌")
        time.sleep(0.014)
    placeholder.markdown(acumulado.strip())
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 8 — MOTOR DE RESUMO AUTOMÁTICO
# ═══════════════════════════════════════════════════════════════════════════════
 
async def maybe_summarize_history(openai_client: AsyncOpenAI) -> None:
    """
    Opera EXCLUSIVAMENTE sobre st.session_state.messages_api.
    O histórico de exibição (messages_display) nunca é tocado — o usuário
    sempre vê a conversa completa na tela.

    Se o histórico da API ultrapassar SUMMARY_TRIGGER_COUNT mensagens de usuário,
    resume as mensagens mais antigas e substitui por uma mensagem compacta de contexto,
    preservando as últimas SUMMARY_KEEP_RECENT mensagens integralmente.
    """
    messages = st.session_state.messages_api
    user_msgs = [m for m in messages if m["role"] == "user"]
 
    if len(user_msgs) <= SUMMARY_TRIGGER_COUNT:
        return
 
    # Localiza o índice de corte preservando as últimas N mensagens
    recent_pairs_found = 0
    cutoff_index = len(messages)
    for i in range(len(messages) - 1, 0, -1):
        if messages[i]["role"] in ("user", "assistant") and not messages[i].get("tool_calls"):
            recent_pairs_found += 1
            if recent_pairs_found >= SUMMARY_KEEP_RECENT:
                cutoff_index = i
                break
 
    to_summarize = [
        m for m in messages[1:cutoff_index]
        if m["role"] in ("user", "assistant")
        and m.get("content")
        and not m.get("tool_calls")
    ]
 
    if len(to_summarize) < 4:
        return
 
    resumo_prompt = [
        {
            "role": "system",
            "content": (
                "Você cria resumos estruturados de conversas de precificação para MEIs. "
                "Extraia em bullet points: dados coletados (custos, taxas, faturamento, estratégia), "
                "fases concluídas e quaisquer decisões tomadas. Seja compacto mas completo. "
                "Responda em português do Brasil."
            ),
        },
        {
            "role": "user",
            "content": (
                "Resuma esta conversa de precificação:\n\n"
                + json.dumps(to_summarize, ensure_ascii=False, indent=2)
            ),
        },
    ]
 
    response = await openai_client.chat.completions.create(
        model=MODEL,
        messages=resumo_prompt,
        max_tokens=600,
    )
 
    if response.usage:
        st.session_state.session_tokens += response.usage.total_tokens
 
    resumo_texto = response.choices[0].message.content.strip()
 
    # Reconstrói APENAS o histórico da API — messages_display permanece intacto
    st.session_state.messages_api = (
        [messages[0]]  # system prompt original
        + [{
            "role": "system",
            "content": (
                f"[RESUMO AUTOMÁTICO DA CONVERSA ANTERIOR]\n"
                f"Os dados abaixo foram extraídos automaticamente do histórico comprimido:\n\n"
                f"{resumo_texto}"
            ),
        }]
        + messages[cutoff_index:]
    )
 
    st.session_state.resumo_ativo = True
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 9 — NÚCLEO DO AGENTE
# ═══════════════════════════════════════════════════════════════════════════════
 
async def query_agent(prompt: str) -> None:
    """
    Fluxo principal do agente.

    Separação de responsabilidades:
    - messages_display: recebe user + assistant em texto limpo. Nunca é comprimido.
    - messages_api: recebe tudo (tool_calls, tool results, etc.) e pode ser resumido.
    Ambos são alimentados em paralelo a cada turno.
    """
    atualizar_contexto_negocio(prompt)
 
    if detectar_sinal_verde(prompt):
        st.session_state.sinal_verde = True
        if st.session_state.fase_protocolo == 4:
            st.session_state.fase_protocolo = 5
        atualizar_sidebar_dinamica()
 
    # Adiciona a mensagem do usuário nos dois históricos
    user_msg = {"role": "user", "content": prompt}
    st.session_state.messages_display.append(user_msg)
    st.session_state.messages_api.append(user_msg)
 
    with st.chat_message("user"):
        st.markdown(prompt)
 
    with st.chat_message("assistant"):
        status_box = st.empty()
 
        if not os.getenv("OPENAI_API_KEY"):
            status_box.error("⚠️ Informe a OPENAI_API_KEY na barra lateral ou no arquivo .env.")
            return
 
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[os.path.join(ROOT, "server.py")],
        )
 
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
 
                    status_box.markdown(
                        '<div class="status-box">🔌 Sincronizando ferramentas de precificação…</div>',
                        unsafe_allow_html=True,
                    )
 
                    tools_response = await session.list_tools()
                    openai_tools = _converter_tools_mcp(tools_response.tools)
                    openai_client = AsyncOpenAI()
                    tool_usada = None
                    resposta_final = ""
 
                    # ── Loop de agente ─────────────────────────────────────────
                    while True:
                        # Usa messages_api (possivelmente resumido) para envio à OpenAI
                        mensagens_api = mensagens_para_api(st.session_state.messages_api)
 
                        if not st.session_state.sinal_verde and st.session_state.fase_protocolo < 5:
                            mensagens_api = mensagens_api + [_lembrete_fase()]
 
                        status_box.markdown(
                            '<div class="status-box">🧠 Consultando o modelo de linguagem…</div>',
                            unsafe_allow_html=True,
                        )
 
                        response = await openai_client.chat.completions.create(
                            model=MODEL,
                            messages=mensagens_api,
                            tools=openai_tools if openai_tools else None,
                        )
 
                        if response.usage:
                            st.session_state.session_tokens += response.usage.total_tokens
                            atualizar_sidebar_dinamica()
 
                        message = response.choices[0].message
 
                        if not message.tool_calls:
                            resposta_final = limpar_resposta(message.content)
                            break
 
                        # Tool calls vão apenas para messages_api (não para display)
                        st.session_state.messages_api.append(message.model_dump(exclude_none=True))
 
                        # ── Executa cada tool call ─────────────────────────────
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                tool_args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                tool_args = {}
 
                            tool_usada = tool_name
                            status_box.markdown(
                                f'<div class="status-box">⚙️ Executando: <code>{tool_name}</code>…</div>',
                                unsafe_allow_html=True,
                            )
 
                            result = await session.call_tool(tool_name, tool_args)
                            result_dict = _parse_tool_result(result)
                            sincronizar_estado_tool(tool_name, tool_args, result_dict)
                            atualizar_sidebar_dinamica()
 
                            # Resultado da tool vai apenas para messages_api
                            st.session_state.messages_api.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(result_dict, ensure_ascii=False),
                            })
 
                        await asyncio.sleep(0.4)
 
                    # ── Resumo automático — opera só em messages_api ───────────
                    await maybe_summarize_history(openai_client)
 
                    status_box.empty()
                    simular_streaming_texto(resposta_final)
 
                    if tool_usada:
                        with st.expander(f"Ferramenta utilizada: {tool_usada}", expanded=False, icon="⚙️"):
                            pass
 
                    # Resposta final vai para os DOIS históricos
                    assistant_msg = {
                        "role": "assistant",
                        "content": resposta_final,
                        "tool_usada": tool_usada,
                    }
                    st.session_state.messages_display.append(assistant_msg)
                    st.session_state.messages_api.append(assistant_msg)
 
        except Exception as exc:
            import traceback
            status_box.error(f"Erro no processamento: {exc}")
            st.code(traceback.format_exc(), language="text")
 
 
# ── Funções privadas de suporte ao agente ──────────────────────────────────────
 
def _converter_tools_mcp(tools_mcp: list) -> list:
    resultado = []
    for tool in tools_mcp:
        bloqueada = (not st.session_state.sinal_verde) and (
            tool.name in TOOLS_CALCULO_FINAL or tool.name in TOOLS_PONTO_EQUILIBRIO
        )
        if not bloqueada:
            resultado.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })
    return resultado
 
 
def _lembrete_fase() -> dict:
    return {
        "role": "system",
        "content": (
            f"[GUARDRAIL INTERNO] Protocolo na {label_fase(st.session_state.fase_protocolo)}. "
            f"Sinal verde NÃO concedido. Colete dados, use ferramentas de diagnóstico, "
            f"mas NÃO chame ferramentas de preço final. Apresente o checklist e aguarde 'Pode calcular'. "
            f"Dados atuais: {json.dumps(st.session_state.dados_precificacao, ensure_ascii=False)}."
        ),
    }
 
 
def _parse_tool_result(result) -> dict:
    try:
        if result.content:
            raw = result.content[0]
            result_text = raw.text if hasattr(raw, "text") else str(raw)
            result_text = result_text.encode('utf-8', errors='ignore').decode('utf-8')
            return json.loads(result_text.strip()) if result_text.strip() else {}
        return {}
    except (json.JSONDecodeError, AttributeError, IndexError) as exc:
        return {"raw_result": str(exc)}
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 10 — CABEÇALHO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════
 
st.title("💰 Assistente de Precificação MEI")
st.caption("Consultoria inteligente com ferramentas de cálculo exato via MCP + OpenAI")
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 11 — RENDERIZAÇÃO DO HISTÓRICO
# Lê de messages_display — nunca comprimido, sempre completo.
# ═══════════════════════════════════════════════════════════════════════════════
 
for msg in st.session_state.messages_display:
    if not deve_exibir(msg):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_usada"):
            with st.expander(f"Ferramenta utilizada: {msg['tool_usada']}", expanded=False, icon="⚙️"):
                pass
 
 
# ═══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 12 — INPUT DO CHAT
# ═══════════════════════════════════════════════════════════════════════════════
 
if prompt := st.chat_input("Como posso te ajudar a precificar hoje?"):
    asyncio.run(query_agent(prompt))