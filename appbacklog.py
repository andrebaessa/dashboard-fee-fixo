# Requisitos: pip install streamlit pandas openpyxl plotly

try:
    import streamlit as st
except ModuleNotFoundError:
    raise ModuleNotFoundError("Streamlit não está instalado. Execute 'pip install streamlit' no terminal.")

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from calendar import month_abbr

st.set_page_config(page_title="Dashboard de Receitas", layout="wide")

# ========= Funções Auxiliares =========
def calcular_roa(df_receita, df_pl):
    df_receita['AnoMes'] = df_receita['DATA'].dt.to_period('M')
    receita_mensal = df_receita.groupby(['Conta', 'AnoMes'])['Receita Líquida'].sum().reset_index()
    receita_mensal = receita_mensal.sort_values(by=['Conta', 'AnoMes'])
    receita_mensal = receita_mensal.merge(df_pl[['Conta', 'PL Total']], on='Conta', how='left')

    receita_mensal['Receita Acumulada'] = receita_mensal.groupby('Conta')['Receita Líquida'].cumsum()
    receita_mensal['Meses Acumulados'] = receita_mensal.groupby('Conta').cumcount() + 1
    receita_mensal['ROA'] = receita_mensal['Receita Acumulada'] / receita_mensal['PL Total']
    receita_mensal['ROA_E'] = ((receita_mensal['Receita Acumulada'] / receita_mensal['Meses Acumulados']) * 12) / receita_mensal['PL Total']

    return receita_mensal

def criar_tabela_receita_roa(df_receita, df_pl):
    df_receita['Mes'] = df_receita['DATA'].dt.strftime('%b')
    traduzir_meses = {
        'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr',
        'May': 'Mai', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
        'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'
    }
    df_receita['Mes'] = df_receita['Mes'].map(traduzir_meses)

    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    receita_pivot = df_receita.groupby(['Assessor Principal', 'Conta', 'Mes'])['Receita Líquida'].sum().reset_index()
    receita_pivot = receita_pivot.pivot_table(index=['Assessor Principal', 'Conta'],
                                              columns='Mes',
                                              values='Receita Líquida',
                                              fill_value=0).reset_index()

    for mes in ordem_meses:
        if mes not in receita_pivot.columns:
            receita_pivot[mes] = 0

    receita_pivot = receita_pivot[['Assessor Principal', 'Conta'] + ordem_meses]
    receita_pivot['Total 2024'] = receita_pivot[ordem_meses].sum(axis=1)
    receita_pivot = receita_pivot.merge(df_pl[['Conta', 'PL Total']], on='Conta', how='left')
    receita_pivot.rename(columns={'PL Total': 'AuC'}, inplace=True)
    receita_pivot['ROA'] = (receita_pivot['Total 2024'] / receita_pivot['AuC']) * 100
    receita_pivot['ROA'] = receita_pivot['ROA'].replace([np.inf, -np.inf], np.nan)
    receita_pivot = receita_pivot.sort_values(by=['Assessor Principal', 'ROA'], ascending=[True, False])

    return receita_pivot

# ========= Interface =========
st.title("📊 Dashboard de Receita e ROA")

arquivo = st.file_uploader("Envie o arquivo Excel com os dados", type=[".xlsx"])

if arquivo:
    df_receita = pd.read_excel(arquivo, sheet_name=0)
    df_pl = pd.read_excel(arquivo, sheet_name=1)

    df_receita['DATA'] = pd.to_datetime(df_receita['DATA'])

    st.sidebar.header("Filtros")
    assessores = st.sidebar.multiselect("Assessor", options=sorted(df_receita['Assessor Principal'].unique()))
    contas = st.sidebar.multiselect("Conta", options=sorted(df_receita['Conta'].unique()))
    categorias = st.sidebar.multiselect("Categoria", options=sorted(df_receita['Categoria'].unique()))
    produtos = st.sidebar.multiselect("Produto", options=sorted(df_receita['Produto'].unique()))

    df_filtrado = df_receita.copy()
    if assessores:
        df_filtrado = df_filtrado[df_filtrado['Assessor Principal'].isin(assessores)]
    if contas:
        df_filtrado = df_filtrado[df_filtrado['Conta'].isin(contas)]
    if categorias:
        df_filtrado = df_filtrado[df_filtrado['Categoria'].isin(categorias)]
    if produtos:
        df_filtrado = df_filtrado[df_filtrado['Produto'].isin(produtos)]

    # === NOVOS INDICADORES ===
    df_filtrado['DATA'] = pd.to_datetime(df_filtrado['DATA'])
    df_filtrado['Ano'] = df_filtrado['DATA'].dt.year
    df_2024 = df_filtrado[df_filtrado['Ano'] == 2024]

    auc_2024 = df_pl[df_pl['Conta'].isin(df_2024['Conta'].unique())]['PL Total'].sum()
    receita_2024 = df_2024['Receita Líquida'].sum()
    roa_total = (receita_2024 / auc_2024) * 100 if auc_2024 != 0 else 0

    st.subheader("📌 Indicadores Gerais 2024")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AuC 2024", f"R$ {auc_2024:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col2:
        st.metric("Receita 2024", f"R$ {receita_2024:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col3:
        st.metric("ROA 2024", f"{roa_total:.2f}%")

    # === NOVOS GRÁFICOS DE PIZZA ===
    st.subheader("📊 Distribuição da Receita por Categoria e Produto")
    col_pie1, col_pie2 = st.columns(2)

    with col_pie1:
        df_cat = df_2024.groupby('Categoria')['Receita Líquida'].sum().reset_index()
        fig_cat = px.pie(df_cat, names='Categoria', values='Receita Líquida', title='Por Categoria')
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_pie2:
        df_prod = df_2024.groupby('Produto')['Receita Líquida'].sum().reset_index()
        fig_prod = px.pie(df_prod, names='Produto', values='Receita Líquida', title='Por Produto')
        st.plotly_chart(fig_prod, use_container_width=True)

    df_roa = calcular_roa(df_filtrado, df_pl)

    st.subheader("📉 Receita Mensal")
    df_filtrado['Mes'] = df_filtrado['DATA'].dt.strftime('%b')
    traduzir_meses = {
        'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr',
        'May': 'Mai', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
        'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'
    }
    df_filtrado['Mes'] = df_filtrado['Mes'].map(traduzir_meses)
    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    receita_mensal = df_filtrado.groupby('Mes')['Receita Líquida'].sum().reindex(ordem_meses).fillna(0).reset_index()
    receita_mensal.columns = ['Mês', 'Receita']
    fig_receita = px.bar(receita_mensal, x='Mês', y='Receita',
                         labels={'Receita': 'Receita Líquida (R$)'}, text_auto='.2s')
    fig_receita.update_layout(yaxis_tickformat=',.2f', yaxis_title='Receita Líquida (R$)', xaxis_title='Mês')
    fig_receita.update_yaxes(separatethousands=True)
    st.plotly_chart(fig_receita, use_container_width=True)

    # GRÁFICO ROAE + ROA com eixo categórico claro
    st.subheader("📈 Evolução do ROAE + ROA Total")
    df_filtrado['DATA'] = pd.to_datetime(df_filtrado['DATA'])
    df_filtrado['MesNum'] = df_filtrado['DATA'].dt.month
    df_filtrado['Ano'] = df_filtrado['DATA'].dt.year
    df_2024 = df_filtrado[df_filtrado['Ano'] == 2024]

    meses_ordenados = [month_abbr[i] for i in range(1, 13)]
    meses_map = dict(zip(range(1, 13), meses_ordenados))

    receita_mensal_roae = df_2024.groupby('MesNum')['Receita Líquida'].sum().reindex(range(1, 13)).fillna(0).reset_index()
    receita_mensal_roae['MesNome'] = receita_mensal_roae['MesNum'].map(meses_map)

    auc_filtrado = df_pl[df_pl['Conta'].isin(df_2024['Conta'].unique())]['PL Total'].sum()
    acumulado = 0
    pontos_roae = []
    for i, row in receita_mensal_roae.iterrows():
        acumulado += row['Receita Líquida']
        media = acumulado / (i + 1)
        roa_e = (media * 12) / auc_filtrado * 100 if auc_filtrado != 0 else 0
        pontos_roae.append(roa_e)

    total_receita = df_2024['Receita Líquida'].sum()
    roa_total = (total_receita / auc_filtrado) * 100 if auc_filtrado != 0 else 0

    x_labels = receita_mensal_roae['MesNome'].tolist() + ['Total 2024']
    y_roae = pontos_roae + [None]
    y_roa_bar = [None] * 12 + [roa_total]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_labels, y=y_roae, mode='lines+markers', name='ROAE (%)'))
    fig.add_trace(go.Bar(x=x_labels, y=y_roa_bar, name='ROA Final (%)'))
    fig.update_layout(
        yaxis_tickformat=',.2f',
        yaxis_title='ROAE / ROA (%)',
        xaxis_title='Mês',
        xaxis=dict(type='category')
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Tabela de Receita por Mês, Total e ROA")
    tabela_final = criar_tabela_receita_roa(df_filtrado, df_pl)
    tabela_formatada = tabela_final.copy()
    for mes in ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez', 'Total 2024', 'AuC']:
        tabela_formatada[mes] = tabela_formatada[mes].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    tabela_formatada['ROA'] = pd.to_numeric(tabela_formatada['ROA'], errors='coerce')
    tabela_formatada['ROA'] = tabela_formatada['ROA'].map(lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else "")

    st.dataframe(tabela_formatada)
    csv_tabela = tabela_final.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Baixar Tabela Final", data=csv_tabela, file_name="tabela_receita_roa.csv", mime="text/csv")

     # === NOVA PLANILHA: PLANILHA GERAL - FEE FIXO ===
    st.subheader("📋 Planilha Geral - Fee Fixo")
    planilha_fee_fixo = tabela_final[
        (
            ((tabela_final['AuC'] >= 100000) & (tabela_final['AuC'] <= 1000000) &
             (tabela_final['ROA'] >= 0.80) & (tabela_final['ROA'] <= 1.20)) |
            ((tabela_final['AuC'] > 1000000) & (tabela_final['AuC'] <= 5000000) &
             (tabela_final['ROA'] >= 0.60) & (tabela_final['ROA'] <= 0.90)) |
            ((tabela_final['AuC'] > 5000000) & (tabela_final['AuC'] <= 10000000) &
             (tabela_final['ROA'] >= 0.48) & (tabela_final['ROA'] <= 0.72)) |
            ((tabela_final['AuC'] > 10000000) &
             (tabela_final['ROA'] >= 0.40) & (tabela_final['ROA'] <= 0.60))
        )
    ].copy()

    planilha_formatada = planilha_fee_fixo.copy()
    for col in ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez', 'Total 2024', 'AuC']:
        if col in planilha_formatada.columns:
            planilha_formatada[col] = planilha_formatada[col].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    planilha_formatada['ROA'] = pd.to_numeric(planilha_formatada['ROA'], errors='coerce')
    planilha_formatada['ROA'] = planilha_formatada['ROA'].map(lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else "")

    st.dataframe(planilha_formatada)
    csv_fee_fixo = planilha_fee_fixo.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Baixar Planilha Geral - Fee Fixo", data=csv_fee_fixo, file_name="planilha_fee_fixo.csv", mime="text/csv")
