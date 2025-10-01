import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import ofxparse
import io
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
import os

# Configuração da página
st.set_page_config(layout="wide", page_title="Dashboard Finanças")

# Título do Dashboard
st.title("📊 Dashboard de Finanças")

# Função para processar arquivo OFX
def processar_ofx(uploaded_file):
    try:
        # Ler o conteúdo do arquivo
        content = uploaded_file.getvalue().decode('ISO-8859-1')
        
        # Processar OFX
        ofx_file = io.StringIO(content)
        ofx = ofxparse.OfxParser.parse(ofx_file)
        
        transactions_data = []
        for account in ofx.accounts:
            for transaction in account.statement.transactions:
                transactions_data.append({
                    "Data": transaction.date.date(),
                    "Valor": float(transaction.amount),
                    "Descrição": transaction.memo,
                    "ID": transaction.id,
                })
        
        df = pd.DataFrame(transactions_data)
        return df
    except Exception as e:
        st.error(f"Erro ao processar arquivo OFX: {e}")
        return None

# Função para categorizar transações
def categorizar_transacoes(df, openai_api_key):
    try:
        template = """
        Você é um analista de dados, trabalhando em um projeto de limpeza de dados.
        Seu trabalho é escolher uma categoria adequada para cada lançamento financeiro
        que vou te enviar.

        Todos são transações financeiras de uma pessoa física.

        Escolha uma dentre as seguintes categorias:
        - Alimentação
        - Receitas
        - Saúde
        - Mercado
        - Educação
        - Compras
        - Transporte
        - Investimento
        - Transferências para terceiros
        - Telefone
        - Moradia
        - Lazer
        - Serviços
        - Outros

        Item a categorizar: {text}

        Responda apenas com o nome da categoria, sem explicações.
        """

        prompt = PromptTemplate.from_template(template=template)
        
        # Configurar o modelo
        chat = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            openai_api_key=openai_api_key
        )
        
        chain = prompt | chat | StrOutputParser()
        
        # Categorizar em lotes para melhor performance
        st.info("Categorizando transações com IA...")
        latest_iteration = st.empty()
        progress_bar = st.progress(0)
        
        categorias = []
        batch_size = 20
        
        for i in range(0, len(df), batch_size):
            batch = list(df["Descrição"].values[i:i+batch_size])
            batch_categorias = chain.batch(batch)
            categorias.extend(batch_categorias)
            latest_iteration.text(f'Iteration {i+1}') 
            progress_bar.progress(min((i + batch_size) / len(df), 1.0))
        
        df["Categoria"] = categorias
        progress_bar.empty()
        st.success("Categorização concluída!")
        return df
        
    except Exception as e:
        st.error(f"Erro na categorização: {e}")
        return None

# Sidebar para upload e configuração
st.sidebar.header("📁 Configurações")

# Upload do arquivo OFX
uploaded_file = st.sidebar.file_uploader(
    "Faça upload do seu extrato OFX", 
    type=['ofx', 'qfx'],
    help="Selecione seu arquivo de extrato bancário no formato OFX"
)

# Input para API Key
api_key_source = st.sidebar.radio(
    "Fonte da API Key:",
    ["Inserir manualmente", "Variável de ambiente"]
)

openai_api_key = None

if api_key_source == "Inserir manualmente":
    openai_api_key = st.sidebar.text_input(
        "OpenAI API Key:", 
        type="password",
        help="Sua chave da API OpenAI. Não será salva."
    )
else:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        st.sidebar.warning("Variável de ambiente OPENAI_API_KEY não encontrada!")
    else:
        st.sidebar.success("API Key carregada do ambiente")

# Processar dados apenas se temos arquivo e API key
if uploaded_file is not None and openai_api_key:
    # Processar OFX
    with st.spinner("Processando arquivo OFX..."):
        df = processar_ofx(uploaded_file)
    
    if df is not None:
        # Categorizar transações
        df = categorizar_transacoes(df, openai_api_key)
        
        if df is not None:
            # Preparar dados para dashboard
            df["Mês"] = df["Data"].apply(lambda x: f"{x.year}-{x.month:02d}")
            
            # Separar receitas e despesas
            df["Tipo"] = df["Valor"].apply(lambda x: "Receita" if x > 0 else "Despesa")
            
            # Para análise de gastos, vamos usar apenas despesas (valores negativos)
            df_despesas = df[df["Valor"] < 0].copy()
            df_despesas["Valor_Absoluto"] = df_despesas["Valor"].abs()
            
            # Armazenar na sessão para uso nos filtros
            st.session_state.df_processed = df
            st.session_state.df_despesas = df_despesas
            
            st.success(f"✅ {len(df)} transações processadas com sucesso!")

# Verificar se temos dados processados
if 'df_processed' in st.session_state and 'df_despesas' in st.session_state:
    df = st.session_state.df_processed
    df_despesas = st.session_state.df_despesas
    
    # Filtros
    st.sidebar.header("🎛️ Filtros")
    
    # Filtro de mês
    meses_disponiveis = sorted(df["Mês"].unique(), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Mês", meses_disponiveis)
    
    # Filtro de categoria
    categorias_disponiveis = df_despesas["Categoria"].unique().tolist()
    categorias_selecionadas = st.sidebar.multiselect(
        "Filtrar por Categorias", 
        categorias_disponiveis, 
        default=categorias_disponiveis
    )
    
    # Aplicar filtros
    def filter_data(df, mes, selected_categories):
        df_filtered = df[df['Mês'] == mes]
        if selected_categories:
            df_filtered = df_filtered[df_filtered['Categoria'].isin(selected_categories)]
        return df_filtered
    
    df_filtered = filter_data(df_despesas, mes_selecionado, categorias_selecionadas)
    
    # ============ NOVO LAYOUT ============
    
    # Seção 1: Estatísticas Principais
    st.subheader("📈 Estatísticas do Mês")
    
    if not df_filtered.empty:
        total_gasto = df_filtered["Valor_Absoluto"].sum()
        num_transacoes = len(df_filtered)
        avg_gasto = total_gasto / num_transacoes if num_transacoes > 0 else 0
        categoria_maior_gasto = df_filtered.groupby("Categoria")["Valor_Absoluto"].sum().idxmax()
        maior_gasto_valor = df_filtered.groupby("Categoria")["Valor_Absoluto"].sum().max()
        
        # Métricas em colunas
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric(
                "Total Gasto", 
                f"R$ {total_gasto:,.2f}",
                help="Soma total de todos os gastos no período"
            )
        
        with stat_col2:
            st.metric(
                "Nº de Transações", 
                num_transacoes,
                help="Quantidade total de transações"
            )
        
        with stat_col3:
            st.metric(
                "Média por Transação", 
                f"R$ {avg_gasto:,.2f}",
                help="Valor médio de cada transação"
            )
        
        with stat_col4:
            st.metric(
                "Maior Categoria", 
                f"{categoria_maior_gasto}",
                f"R$ {maior_gasto_valor:,.2f}",
                help="Categoria com maior gasto total"
            )
    else:
        st.warning("Nenhum dado disponível para os filtros selecionados.")
    
    # Seção 2: Gráficos de Distribuição por Categoria
    st.subheader("📊 Distribuição por Categoria")
    
    if not df_filtered.empty:
        category_distribution = df_filtered.groupby("Categoria")["Valor_Absoluto"].sum().reset_index()
        
        # Três colunas para os gráficos
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        with chart_col1:
            # Gráfico de Pizza
            fig_pie = px.pie(
                category_distribution, 
                values='Valor_Absoluto', 
                names='Categoria', 
                title='<b>Distribuição em Pizza</b>',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}'
            )
            fig_pie.update_layout(
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with chart_col2:
            # Gráfico de Barras Horizontal
            fig_bar_h = px.bar(
                category_distribution.sort_values('Valor_Absoluto', ascending=True),
                y='Categoria',
                x='Valor_Absoluto',
                title='<b>Distribuição em Barras</b>',
                color='Valor_Absoluto',
                color_continuous_scale='Blues',
                orientation='h'
            )
            fig_bar_h.update_layout(
                height=400,
                xaxis_title="Valor (R$)",
                yaxis_title="",
                showlegend=False
            )
            fig_bar_h.update_traces(
                hovertemplate='<b>%{y}</b><br>R$ %{x:,.2f}'
            )
            st.plotly_chart(fig_bar_h, use_container_width=True)
        
        with chart_col3:
            # Gráfico de Rosca (Donut)
            fig_donut = px.pie(
                category_distribution, 
                values='Valor_Absoluto', 
                names='Categoria', 
                title='<b>Visão em Rosca</b>',
                hole=0.6,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_donut.update_traces(
                textposition='outside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}'
            )
            fig_donut.update_layout(
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_donut, use_container_width=True)
    
    # Seção 3: Evolução Temporal
    st.subheader("📅 Evolução Temporal dos Gastos")
    
    if not df_filtered.empty:
        timeline_col1, timeline_col2 = st.columns([0.7, 0.3])
        
        with timeline_col1:
            # Gráfico de Linha
            timeline_data = df_filtered.groupby("Data")["Valor_Absoluto"].sum().reset_index()
            fig_timeline = px.line(
                timeline_data, 
                x='Data', 
                y='Valor_Absoluto',
                title='<b>Gastos ao Longo do Tempo</b>',
                markers=True,
                line_shape='spline'
            )
            fig_timeline.update_layout(
                xaxis_title="Data",
                yaxis_title="Valor (R$)",
                hovermode='x unified'
            )
            fig_timeline.update_traces(
                hovertemplate='<b>%{x}</b><br>R$ %{y:,.2f}',
                line=dict(width=3)
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        with timeline_col2:
            # Top 5 Transações
            st.subheader("🏆 Top 5 Maiores Gastos")
            top_transacoes = df_filtered.nlargest(5, 'Valor_Absoluto')[['Data', 'Descrição', 'Valor_Absoluto']]
            for idx, row in top_transacoes.iterrows():
                st.write(f"**R$ {row['Valor_Absoluto']:,.2f}**")
                st.caption(f"{row['Data'].strftime('%d/%m')} - {row['Descrição'][:30]}...")
                st.divider()
    
    # Seção 4: Tabela de Transações (agora no final)
    st.subheader("📋 Detalhamento das Transações")
    
    if not df_filtered.empty:
        # Mostrar tabela com opção de expandir/contrair
        with st.expander("Visualizar Todas as Transações", expanded=False):
            st.dataframe(
                df_filtered[["Data", "Descrição", "Categoria", "Valor_Absoluto"]]
                .rename(columns={"Valor_Absoluto": "Valor"})
                .sort_values("Data", ascending=False)
                .style.format({
                    'Valor': 'R$ {:.2f}',
                    'Data': lambda x: x.strftime('%d/%m/%Y')
                }),
                use_container_width=True,
                height=400
            )
    else:
        st.warning("Nenhuma transação encontrada para os filtros selecionados.")

else:
    # Mensagem inicial
    st.markdown("""
    ## 👋 Bem-vindo ao seu Dashboard de Finanças!
    
    Para começar:
    1. **Faça upload** do seu extrato bancário no formato OFX
    2. **Configure** sua API Key da OpenAI
    3. **Aguarde** o processamento dos dados
    
    ### 📝 Como obter seu extrato OFX:
    - **Itaú**: Internet Banking > Extrato > Exportar > OFX
    - **Bradesco**: Internet Banking > Extrato > Exportar
    - **Santander**: Internet Banking > Extrato > Download
    - **Outros bancos**: Procure por "Exportar OFX" ou "Quicken format"
    
    ### 🔒 Segurança:
    - Seus dados **nunca são salvos**
    - Processamento ocorre **localmente** na sua sessão
    - Arquivos **não são enviados** para o GitHub
    """)

# Limpar dados da sessão
if st.sidebar.button("🔄 Limpar Dados"):
    for key in ['df_processed', 'df_despesas']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()