import math

class Precificacao:

    def _calcular_markup(
            self,
            despesas_variaveis: float,
            despesas_fixas: float,
            lucro_pretendido: float
    ) -> float:
        """
        Calcula o markup multiplicador a partir dos percentuais de custos e lucro.

        O markup é o fator pelo qual o custo de produção deve ser multiplicado
        para gerar um preço de venda que cubra todas as despesas e ainda entregue
        o lucro desejado. É um método interno usado pelos métodos públicos de
        precificação — não deve ser chamado diretamente pelo MCP.

        Fórmula: markup = 100 / (100 - (DV + DF + LP))
        Onde DV = despesas variáveis, DF = despesas fixas, LP = lucro pretendido.

        Args:
            despesas_variaveis: percentual (%) de custos que variam com cada venda.
            despesas_fixas: percentual (%) dos custos fixos do negócio rateados.
            lucro_pretendido: percentual (%) de lucro líquido desejado.

        Returns:
            float: o markup calculado, sempre maior que 1.0.

        Raises:
            ValueError: se a soma dos três percentuais for >= 100 ou negativa.
        """
        soma_percentuais = despesas_variaveis + despesas_fixas + lucro_pretendido

        if soma_percentuais >= 100:
            raise ValueError(
                "A soma de despesas variáveis, despesas fixas e lucro pretendido "
                "deve ser menor que 100%."
            )

        if soma_percentuais < 0:
            raise ValueError(
                "A soma dos percentuais não pode ser negativa."
            )

        return 100 / (100 - soma_percentuais)

    def _calcular_custo_unitario(
            self,
            custo_total: float,
            quantidade: int
    ) -> float:
        """
        Calcula quanto custa produzir uma única unidade de um produto feito em lote.
        """
        if custo_total <= 0:
            raise ValueError("O custo total deve ser maior que zero.")

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        return custo_total / quantidade

    def calcular_preco_unitario(
            self,
            custo_total: float,
            quantidade: int,
            despesas_variaveis: float,
            despesas_fixas: float,
            lucro_pretendido: float
    ) -> dict:
        """
        Calcula o preço de venda ideal para produtos fabricados em lote (quantidade).

        Use este método quando o empreendedor produz múltiplas unidades de um mesmo
        produto em uma única produção — por exemplo: fez 100 brigadeiros gastando
        R$50 no total, ou produziu 30 sabonetes artesanais com R$90 em insumos.

        Args:
            custo_total: valor total em reais investido na produção do lote inteiro.
            quantidade: número de unidades produzidas no lote.
            despesas_variaveis: percentual (%) de custos dinâmicos por venda.
            despesas_fixas: percentual (%) dos custos fixos alocados sobre o produto.
            lucro_pretendido: percentual (%) de lucro líquido desejado.

        Returns:
            dict: custo_unitario, markup, preco_unitario e preco_total do lote.
        """
        custo_unitario = self._calcular_custo_unitario(custo_total, quantidade)
        markup = self._calcular_markup(despesas_variaveis, despesas_fixas, lucro_pretendido)
        preco_unitario = custo_unitario * markup
        preco_total = preco_unitario * quantidade

        return {
            "custo_unitario": round(custo_unitario, 2),
            "markup": round(markup, 4),
            "preco_unitario": round(preco_unitario, 2),
            "preco_total": round(preco_total, 2)
        }

    def calcular_produto_unico(
            self,
            custo_producao: float,
            despesas_variaveis: float,
            despesas_fixas: float,
            lucro_pretendido: float
    ) -> dict:
        """
        Calcula o preço de venda ideal para produtos únicos ou serviços individuais.

        Use este método quando o produto é feito individualmente, sem produção em lote
        — por exemplo: um quadro pintado à mão, um bolo personalizado encomendado,
        uma bolsa de crochê sob medida ou um serviço/manutenção individual.

        Args:
            custo_producao: valor em reais gasto para entregar este item ou serviço específico.
            despesas_variaveis: percentual (%) de custos dinâmicos por venda.
            despesas_fixas: percentual (%) dos custos fixos estruturais do negócio.
            lucro_pretendido: percentual (%) de lucro líquido desejado.

        Returns:
            dict: custo_producao original, markup e o preco_final recomendado.
        """
        if custo_producao <= 0:
            raise ValueError("O custo de produção deve ser maior que zero.")

        markup = self._calcular_markup(despesas_variaveis, despesas_fixas, lucro_pretendido)
        preco_final = custo_producao * markup

        return {
            "custo_producao": round(custo_producao, 2),
            "markup": round(markup, 4),
            "preco_final": round(preco_final, 2)
        }

    # ─── NOVAS FERRAMENTAS AGREGADAS PARA SUPORTE E SEGURANÇA DA IA ──────────────────

    def consolidar_despesas_variaveis(
            self,
            taxa_maquininha_cartao: float = 0.0,
            comissao_marketplace: float = 0.0,
            imposto_sobre_venda: float = 0.0,
            outros_percentuais: float = 0.0
    ) -> dict:
        """
        Agrupa e soma múltiplos custos variáveis percentuais (%) comuns em vendas de MEIs.

        Pequenos empreendedores frequentemente lidam com várias taxas dinâmicas em uma única venda 
        (ex: a taxa do cartão de crédito, a comissão da plataforma de entrega e o imposto). Esta 
        ferramenta centraliza esses valores, somando-os para entregar o percentual total de 
        despesas variáveis necessário para o cálculo do Markup.

        DIRETRIZ CRÍTICA DE PRECIFICAÇÃO PARA A IA (RESOLUÇÃO DE ERROS NOMINAIS):
        Se o usuário relatar uma despesa variável que possui um VALOR FIXO EM REAIS por unidade de 
        venda (por exemplo: 'pago R$ 4,00 pela caixa de correio' ou 'a plataforma me cobra R$ 6,00 
        fixos por venda executada'), você NÃO deve colocar esse valor nominal nesta ferramenta. 
        Instrua o usuário de que custos fixos em reais por unidade devem ser somados DIRETAMENTE 
        junto ao custo de produção/insumos do produto. Valores nominais em reais entram no custo bruto; 
        apenas taxas puramente percentuais (%) entram aqui.

        Como explicar o resultado ao MEI:
        Apresente o somatório das taxas e diga que esse percentual representa a fatia que os 
        intermediários financeiros e de vendas vão retirar do preço final de cada produto comercializado.

        Args:
            taxa_maquininha_cartao: Percentual (%) cobrado pela máquina de cartão ou gateway (ex: 3.5).
            comissao_marketplace: Percentual (%) de plataformas (ex: Mercado Livre, Shopee, iFood) (ex: 11.0).
            imposto_sobre_venda: Percentual (%) de impostos diretos sobre a nota emitida (ex: 4.0).
            outros_percentuais: Outras taxas proporcionais ao preço final (ex: comissões de vendedores).

        Returns:
            dict contendo:
                - despesas_variaveis_totais (float): O somatório de todas as taxas percentuais pronto para o Markup.
                - resumo_taxas (dict): Espelho detalhado dos valores processados para conferência.
        """
        if any(v < 0 for v in [taxa_maquininha_cartao, comissao_marketplace, imposto_sobre_venda, outros_percentuais]):
            raise ValueError("Atenção: nenhuma taxa ou percentual de despesa pode ser um valor negativo.")

        total = taxa_maquininha_cartao + comissao_marketplace + imposto_sobre_venda + outros_percentuais

        return {
            "despesas_variaveis_totais": round(total, 2),
            "resumo_taxas": {
                "maquininha_cartao": taxa_maquininha_cartao,
                "marketplace_plataforma": comissao_marketplace,
                "imposto": imposto_sobre_venda,
                "outros": outros_percentuais
            }
        }

    def converter_custo_fixo_para_percentual(
            self,
            custo_fixo_mensal: float,
            faturamento_mensal: float
    ) -> dict:
        """
        Transforma os custos fixos nominais em reais (R$) no percentual (%) correspondente ao faturamento.

        Microempreendedores sabem o valor exato do aluguel ou da internet em reais, mas o método de 
        precificação por Markup exige que esses custos estruturais sejam convertidos em percentual. 
        Esta ferramenta resolve isso dividindo o custo fixo estrutural total pelo faturamento mensal 
        (real ou estimado) informado pelo empreendedor.

        Como explicar o resultado ao MEI:
        Explique que o percentual retornado representa a fatia exata de cada venda que será 
        obrigatoriamente separada apenas para pagar a estrutura e manter as portas abertas, antes de 
        cobrir os custos do material do próprio produto ou do lucro.

        Args:
            custo_fixo_mensal: Soma total em reais das contas fixas mensais do negócio (ex: aluguel, DAS, internet).
            faturamento_mensal: Faturamento total em reais bruto que a empresa gera ou projeta faturar no mês.

        Returns:
            dict contendo:
                - percentual (float): O peso percentual do custo fixo sobre o faturamento.
                - explicacao (str): Texto didático pronto para ser integrado à narrativa com o usuário.
        """
        if faturamento_mensal <= 0:
            raise ValueError("O faturamento mensal estimado deve ser maior que zero para evitar divisão por zero.")
        if custo_fixo_mensal < 0:
            raise ValueError("O custo fixo mensal estrutural não pode ser um valor negativo.")

        percentual = (custo_fixo_mensal / faturamento_mensal) * 100
        
        explicacao = (
            f"Seu custo fixo de R$ {custo_fixo_mensal:.2f} representa {percentual:.2f}% "
            f"do faturamento mensal estimado de R$ {faturamento_mensal:.2f}."
        )

        return {
            "percentual": round(percentual, 2),
            "explicacao": explicacao
        }

    def validar_percentuais(
            self,
            despesas_variaveis: float,
            despesas_fixas: float,
            lucro_pretendido: float
    ) -> dict:
        """
        Verifica preventivamente se a combinação de despesas e lucros permite um cálculo matematicamente viável.

        Atua como um guardião matemático. Se a soma de (Despesas Variáveis + Despesas Fixas + Lucro Pretendido) 
        for igual ou maior que 100%, a conta de Markup quebra (gerando divisão por zero ou números negativos). 
        Isso indica na realidade do negócio que a soma das taxas estruturais e da ambição de lucro consumiram 
        todo o valor comercial do produto, inviabilizando cobrir os materiais de fabricação.

        Como agir com base no retorno:
        - Se 'valido' for True: Siga em frente para o cálculo final de preço.
        - Se 'valido' for False: Interrompa o fluxo de precificação imediatamente. Explique de maneira acolhedora 
          que a combinação atual ultrapassa os limites sustentáveis da precificação por markup e que eles precisam 
          rever as metas de despesas ou planejar um faturamento maior.

        Args:
            despesas_variaveis: Percentual (%) de custos variáveis totais (calculado previamente).
            despesas_fixas: Percentual (%) de despesas fixas estruturais (calculado previamente).
            lucro_pretendido: Percentual (%) de margem de lucro líquido desejado pelo MEI sobre a venda.

        Returns:
            dict contendo:
                - valido (bool): True se a operação matemática for segura; False se for impossível.
                - soma (float): O somatório dos três percentuais passados.
                - mensagem (str): Uma explicação amigável detalhando a saúde ou a inviabilidade da combinação.
        """
        if despesas_variaveis < 0 or despesas_fixas < 0 or lucro_pretendido < 0:
            return {
                "valido": False,
                "soma": round(despesas_variaveis + despesas_fixas + lucro_pretendido, 2),
                "mensagem": "Erro de entrada: os percentuais informados não podem conter valores negativos."
            }

        soma = despesas_variaveis + despesas_fixas + lucro_pretendido

        if soma >= 100:
            mensagem = (
                f"A soma das suas taxas e despesas com o lucro desejado somou {soma:.2f}%. "
                f"Como esse total atingiu ou passou de 100%, o cálculo se tornou inviável. Isso significa "
                f"que as despesas de intermediação e a margem de lucro sozinhas consumiram todo o preço de venda, "
                f"sem deixar margem para pagar os custos de produção. Precisamos reajustar esses alvos!"
            )
            return {
                "valido": False,
                "soma": round(soma, 2),
                "mensagem": mensagem
            }

        return {
            "valido": True,
            "soma": round(soma, 2),
            "mensagem": f"Combinação válida! Seus percentuais somam {soma:.2f}%, restando uma margem saudável de proteção para cobrir os insumos do produto."
        }

    def calcular_ponto_de_equilibrio(
            self,
            custos_fixos_mensais: float,
            preco_unitario: float,
            custo_unitario: float
    ) -> dict:
        """
        Calcula o Ponto de Equilíbrio operacional mensal (Break-even Point) em unidades e faturamento.

        Responde à dúvida de viabilidade comercial mais frequente dos MEIs: 
        "Quantas unidades exatas deste produto eu preciso vender por mês para conseguir pagar todas as contas da empresa?".
        
        A ferramenta calcula a Margem de Contribuição Unitária (Preço - Custo Unitário), que é o valor que de 
        fato sobra de cada venda realizada para ir se acumulando no caixa até liquidar o custo fixo da estrutura.

        Como explicar o resultado ao MEI:
        Diga de forma direta: "Para pagar sua estrutura de custos fixos, você precisa vender no mínimo X unidades 
        deste produto no mês, atingindo um faturamento mínimo de R$ Y. A partir da unidade X+1, você terá lucro real."

        Args:
            custos_fixos_mensais: O valor nominal total em REAIS das despesas fixas estruturais por mês (ex: R$ 800.00).
            preco_unitario: O preço final de venda em REAIS que foi calculado para o produto ou serviço.
            custo_unitario: O custo direto em REAIS de produção/insumos de uma única unidade (ou item do lote).

        Returns:
            dict contendo:
                - unidades_minimas (int): Meta mínima de vendas no mês (arredondada para cima, pois não se vende fração de item).
                - faturamento_minimo (float): O faturamento bruto necessário para empatar as contas mensais.
                - margem_contribuicao_un (float): O valor em reais que sobra limpo de cada unidade vendida para pagar o custo fixo.
        """
        if custos_fixos_mensais < 0:
            raise ValueError("Os custos fixos mensais estruturais não podem ser negativos.")
        if preco_unitario <= 0 or custo_unitario <= 0:
            raise ValueError("O preço unitário calculado e o custo unitário de produção devem ser maiores que zero.")

        margem_contribuicao = preco_unitario - custo_unitario

        if margem_contribuicao <= 0:
            raise ValueError(
                "O preço unitário de venda recomendado está menor ou igual ao custo de produção. Isso significa que "
                "o produto gera prejuízo direto a cada venda, tornando matematicamente impossível pagar as contas fixas do negócio."
            )

        unidades_minimas = math.ceil(custos_fixos_mensais / margem_contribuicao)
        faturamento_minimo = unidades_minimas * preco_unitario

        return {
            "unidades_minimas": unidades_minimas,
            "faturamento_minimo": round(faturamento_minimo, 2),
            "margem_contribuicao_un": round(margem_contribuicao, 2)
        }

    def simular_cenarios_de_lucro(
            self,
            custo_producao: float,
            despesas_variaveis: float,
            despesas_fixas: float
    ) -> dict:
        """
        Simula automaticamente três opções de preços comerciais baseadas em metas distintas de lucro líquido.

        Impede que o microempreendedor precise 'chutar' uma margem de lucro sem critérios comerciais claros. 
        A ferramenta calcula três perfis estruturados de lucro sobre os custos e taxas enviados:
          1. Conservador (15% de lucro): Preço de combate mais baixo, excelente para penetração de mercado ou queima de estoque.
          2. Moderado (25% de lucro): O patamar ideal, seguro e equilibrado para a sustentabilidade de comércios e artesanias.
          3. Arrojado (40% de lucro): Preço premium mais alto, voltado para produtos de alta exclusividade ou encomendas personalizadas.

        Como apresentar ao MEI:
        Exiba os três preços sugeridos explicando a estratégia competitiva de cada um para que o empreendedor decida 
        com autonomia qual cenário se adapta melhor ao bolso dos clientes dele e aos preços da concorrência.

        Args:
            custo_producao: Custo bruto de materiais do item único ou custo por unidade obtido do lote em REAIS.
            despesas_variaveis: Percentual (%) total de custos por venda (taxas de transação/plataformas).
            despesas_fixas: Percentual (%) de despesas estruturais calculado sobre o faturamento do negócio.

        Returns:
            dict contendo chaves para os cenários ('conservador', 'moderado', 'arrojado'), cada uma contendo:
                - lucro_percentual (float): A margem líquida simulada.
                - markup (float): O fator multiplicador resultante.
                - preco_final (float): O preço final de venda gerado para aquele cenário.
                - viavel (bool): Sinaliza se a simulação foi bem-sucedida ou se os custos atuais inviabilizaram a margem.
        """
        cenarios = {
            "conservador": 15.0,
            "moderado": 25.0,
            "arrojado": 40.0
        }
        
        resultado_simulacao = {}

        for perfil, lucro in cenarios.items():
            try:
                calculo = self.calcular_produto_unico(
                    custo_producao=custo_producao,
                    despesas_variaveis=despesas_variaveis,
                    despesas_fixas=despesas_fixas,
                    lucro_pretendido=lucro
                )
                resultado_simulacao[perfil] = {
                    "lucro_percentual": lucro,
                    "markup": calculo["markup"],
                    "preco_final": calculo["preco_final"],
                    "viavel": True
                }
            except ValueError:
                resultado_simulacao[perfil] = {
                    "lucro_percentual": lucro,
                    "viavel": False,
                    "erro": "Inviável. As despesas atuais somadas impedem o alcance desta meta de lucro líquido."
                }

        return resultado_simulacao