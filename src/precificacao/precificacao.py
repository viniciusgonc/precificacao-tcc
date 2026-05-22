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
            despesas_variaveis: percentual (%) de custos que variam com cada venda,
                como taxas de marketplace, comissão de vendedor, embalagem por unidade.
                Exemplo: 10.0 representa 10%.
            despesas_fixas: percentual (%) dos custos fixos do negócio rateados sobre
                o produto, como aluguel, energia elétrica, internet, contador.
                Exemplo: 15.0 representa 15%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                de venda final. Exemplo: 20.0 representa 20%.

        Returns:
            float: o markup calculado, sempre maior que 1.0.

        Raises:
            ValueError: se a soma dos três percentuais for >= 100, pois tornaria
                o markup matematicamente impossível (divisão por zero ou negativo).
            ValueError: se a soma dos percentuais for negativa.
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

        Divide o custo total de produção do lote pela quantidade produzida.
        É um método interno auxiliar — não deve ser chamado diretamente pelo MCP.

        Exemplo: se o empreendedor gastou R$50 para fazer 100 brigadeiros,
        o custo unitário é R$0,50 por brigadeiro.

        Args:
            custo_total: valor total em reais gasto para produzir o lote completo,
                incluindo matéria-prima, embalagem, gás, ingredientes, etc.
                Deve ser maior que zero.
            quantidade: número total de unidades produzidas no lote.
                Deve ser um número inteiro positivo maior que zero.

        Returns:
            float: custo de produção por unidade em reais.

        Raises:
            ValueError: se custo_total for menor ou igual a zero.
            ValueError: se quantidade for menor ou igual a zero.
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

        O método divide o custo total pela quantidade para obter o custo unitário,
        depois aplica o markup para chegar ao preço de venda que garante a cobertura
        de todas as despesas e o lucro desejado.

        Etapas internas:
            1. Calcula o custo unitário: custo_total / quantidade
            2. Calcula o markup: 100 / (100 - (DV + DF + LP))
            3. Calcula o preço unitário: custo_unitario × markup
            4. Calcula o preço total: preco_unitario × quantidade

        Exemplos de uso:
            - Brigadeiros: 100 unidades com custo total de R$50
            - Cosméticos artesanais: 20 potes com custo total de R$180
            - Velas decorativas: 50 unidades com custo total de R$200

        Args:
            custo_total: valor total em reais investido na produção do lote inteiro
                (matéria-prima, embalagens, energia, etc.). Deve ser maior que zero.
            quantidade: número de unidades produzidas no lote. Deve ser maior que zero.
            despesas_variaveis: percentual (%) de custos que incidem sobre cada venda,
                como taxas de cartão, comissões, frete. Exemplo: 5.0 para 5%.
            despesas_fixas: percentual (%) dos custos fixos mensais do negócio
                alocados sobre o produto, como aluguel e energia. Exemplo: 10.0 para 10%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                final de venda. Exemplo: 20.0 para 20%.

        Returns:
            dict com as seguintes chaves:
                - custo_unitario (float): custo de produção por unidade em reais
                - markup (float): fator multiplicador calculado (ex: 1.4286)
                - preco_unitario (float): preço de venda recomendado por unidade em reais
                - preco_total (float): faturamento total esperado ao vender todo o lote

        Raises:
            ValueError: se custo_total ou quantidade forem inválidos.
            ValueError: se a soma dos percentuais for >= 100% ou negativa.
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
        um conserto de eletrodoméstico, uma sessão de fotografia ou qualquer serviço
        onde o custo já se refere àquela entrega específica.

        Diferente do cálculo por quantidade, aqui o custo de produção já é o custo
        daquele produto ou serviço específico — não há divisão por quantidade.
        O markup é aplicado diretamente sobre esse custo para gerar o preço final.

        Exemplos de uso:
            - Artesanato sob encomenda: bolsa de crochê com R$35 em materiais
            - Serviço de design: logo criado com R$0 em custo direto, mas com horas trabalhadas valoradas
            - Bolo personalizado: encomenda específica com R$80 em ingredientes
            - Manutenção: reparo de equipamento com R$40 em peças

        Args:
            custo_producao: valor em reais gasto para produzir ou entregar este produto
                ou serviço específico (materiais, insumos, horas, deslocamento, etc.).
                Deve ser maior que zero.
            despesas_variaveis: percentual (%) de custos que incidem sobre cada venda,
                como taxas de pagamento, comissões, frete. Exemplo: 5.0 para 5%.
            despesas_fixas: percentual (%) dos custos fixos mensais do negócio
                alocados sobre este produto, como aluguel e energia. Exemplo: 10.0 para 10%.
            lucro_pretendido: percentual (%) de lucro líquido desejado sobre o preço
                final de venda. Exemplo: 20.0 para 20%.

        Returns:
            dict com as seguintes chaves:
                - custo_producao (float): custo original informado, em reais
                - markup (float): fator multiplicador calculado (ex: 1.8182)
                - preco_final (float): preço de venda recomendado em reais

        Raises:
            ValueError: se custo_producao for menor ou igual a zero.
            ValueError: se a soma dos percentuais for >= 100% ou negativa.
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

    # ─── MÉTODOS DE SUPORTE E SEGURANÇA SINCRO COM SERVER.PY ────────────────────────

    def consolidar_despesas_variaveis(
            self,
            taxa_maquininha_cartao: float = 0.0,
            comissao_marketplace: float = 0.0,
            imposto_sobre_venda: float = 0.0,
            outros_percentuais: float = 0.0
    ) -> dict:
        """
        Agrupa e soma múltiplos custos variáveis percentuais (%) comuns em vendas de MEIs.
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

    # ─── NOVO MÉTODO COMPATÍVEL COM MARGEM DE CONTRIBUIÇÃO ALVO ──────────────────────

    def calcular_preco_por_margem_contribuicao(
            self,
            custo_unitario: float,
            despesas_variaveis: float,
            margem_contribuicao_alvo: float
    ) -> dict:
        """
        Calcula o preço de venda ideal com base em uma meta de Margem de Contribuição Alvo (%).

        Esta metodologia resolve o problema do 'Círculo Vicioso do Markup', impedindo que custos 
        fixos altos de estrutura rateados sobre faturamentos pequenos distorçam o preço final 
        de itens de alto giro (evitando um energético inviável comercialmente). 
        
        Em vez de embutir os custos fixos estruturais de forma nominal, define-se uma margem 
        percentual realista e mercadológica que cada unidade vendida reterá. Esse saldo gerado 
        entrará no caixa geral para ajudar a pagar a estrutura fixa estrutural da empresa.

        Como explicar o resultado ao MEI:
        Apresente o preço calculado e enfatize o valor em reais da Margem de Contribuição. Explique 
        didaticamente que esses reais que 'sobram' de cada venda não são o lucro puro imediato, mas 
        sim a força de contribuição daquele produto para pagar o aluguel e as contas de luz da loja.

        Args:
            custo_unitario: O custo direto de aquisição ou matéria-prima de uma unidade em REAIS (ex: 10.0).
            despesas_variaveis: Percentual (%) de custos dinâmicos associados exclusivamente à venda (taxas de cartão).
            margem_contribuicao_alvo: Percentual (%) do preço final de venda que deve sobrar limpo para pagar os custos fixos estruturais e gerar o lucro global da empresa.

        Returns:
            dict contendo:
                - custo_unitario (float): O custo unitário original de aquisição.
                - despesas_variaveis_percentual (float): O percentual de taxas dinâmicas aplicado.
                - margem_contribuicao_alvo_percentual (float): O percentual de margem alvo definido.
                - margem_contribuicao_reais (float): O valor em reais gerado por unidade para cobrir a estrutura fixa.
                - preco_venda (float): O preço final sugerido de vitrine.

        Raises:
            ValueError: Se custo_unitario for menor ou igual a zero.
            ValueError: Se despesas_variaveis ou margem_contribuicao_alvo forem inválidos ou somados atingirem >= 100%.
        """
        if custo_unitario <= 0:
            raise ValueError("O custo unitário do produto deve ser maior que zero.")
        if despesas_variaveis < 0 or margem_contribuicao_alvo <= 0:
            raise ValueError("As despesas variáveis não podem ser negativas e a margem de contribuição alvo deve ser maior que zero.")

        soma_percentuais = despesas_variaveis + margem_contribuicao_alvo

        if soma_percentuais >= 100:
            raise ValueError(
                f"A combinação de despesas variáveis ({despesas_variaveis}%) e margem de contribuição alvo "
                f"({margem_contribuicao_alvo}%) somou {soma_percentuais}%. O cálculo é inviável porque a soma das "
                f"taxas e da margem de contribuição atingiu ou passou de 100% do valor do produto."
            )

        # Fórmula matemática linear descontando as taxas e a margem do denominador
        preco_venda = (custo_unitario * 100) / (100 - soma_percentuais)
        
        # Valor real em dinheiro que sobra por unidade para empurrar as despesas fixas para baixo
        margem_reais = preco_venda * (margem_contribuicao_alvo / 100)

        return {
            "custo_unitario": round(custo_unitario, 2),
            "despesas_variaveis_percentual": round(despesas_variaveis, 2),
            "margem_contribuicao_alvo_percentual": round(margem_contribuicao_alvo, 2),
            "margem_contribuicao_reais": round(margem_reais, 2),
            "preco_venda": round(preco_venda, 2)
        }