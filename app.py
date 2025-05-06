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

# Estilo visual customizado
st.markdown("""
    <style>
        .stApp {
            background-color: #f8f8f8;
        }

        div[data-testid="stMetric"] {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            margin: 5px;
            background-color: #ffffff;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
            color: #474747;
        }

        section[data-testid="stFileUploader"] {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 6px 10px;
            background-color: #fff;
            box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
            width: 100% !important;
        }

        div[data-testid="stVerticalBlock"] > div:has(.js-plotly-plot),
        div[data-testid="stDataFrameContainer"] {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
            background-color: #ffffff;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.05);
        }

        button[kind="primary"] {
            border-radius: 8px;
            background-color: #37cc84;
            color: white;
            font-weight: bold;
        }

        button[kind="primary"]:hover {
            background-color: #2fa36a;
        }
    </style>
""", unsafe_allow_html=True)



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

def calcular_roa_referencia(auc):
    if auc >= 100000 and auc <= 1000000:
        return 1.00
    elif auc > 1000000 and auc <= 5000000:
        return 0.75
    elif auc > 5000000 and auc <= 10000000:
        return 0.60
    elif auc > 10000000:
        return 0.50
    else:
        return None

def criar_tabela_receita_roa(df_receita, df_pl):
    df_receita['Mes'] = df_receita['DATA'].dt.strftime('%b')
    traduzir_meses = {
        'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr',
        'May': 'Mai', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago',
        'Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'
    }
    df_receita['Mes'] = df_receita['Mes'].map(traduzir_meses)
    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun','Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    receita_pivot = df_receita.groupby(['Assessor Principal', 'Conta', 'Mes'])['Receita Líquida'].sum().reset_index()
    receita_pivot = receita_pivot.pivot_table(index=['Assessor Principal', 'Conta'], columns='Mes', values='Receita Líquida', fill_value=0).reset_index()
    for mes in ordem_meses:
        if mes not in receita_pivot.columns:
            receita_pivot[mes] = 0
    receita_pivot = receita_pivot[['Assessor Principal', 'Conta'] + ordem_meses]
    receita_pivot['Total 2024'] = receita_pivot[ordem_meses].sum(axis=1)
    receita_pivot = receita_pivot.merge(df_pl[['Conta', 'PL Total']], on='Conta', how='left')
    receita_pivot.rename(columns={'PL Total': 'AuC'}, inplace=True)
    receita_pivot['ROA'] = (receita_pivot['Total 2024'] / receita_pivot['AuC']) * 100
    receita_pivot['ROA'] = receita_pivot['ROA'].replace([np.inf, -np.inf], np.nan)
    receita_pivot['ROA Referência'] = receita_pivot['AuC'].apply(calcular_roa_referencia)
    receita_pivot = receita_pivot.sort_values(by=['Assessor Principal', 'ROA'], ascending=[True, False])
    return receita_pivot

# ========= Interface =========
st.markdown(
    """
    <h1 style="display: flex; align-items: center; gap: 12px;">
        <img src="https://static.wixstatic.com/media/38e555_b3f9ec3d803e479084d5c1c098e0ff77~mv2.png/v1/fill/w_60,h_51,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/38e555_b3f9ec3d803e479084d5c1c098e0ff77~mv2.png" width="50" />
        Dashboard - Fee Fixo
    </h1>
    """,
    unsafe_allow_html=True
)


with st.container():
    col_esq, _ = st.columns([1, 6])
    with col_esq:
        arquivo = st.file_uploader("", type=[".xlsx"], label_visibility="collapsed")


if arquivo:
    # === Leitura e preparação ===
    df_receita = pd.read_excel(arquivo, sheet_name=0)
    df_pl = pd.read_excel(arquivo, sheet_name=1)

    df_receita['DATA'] = pd.to_datetime(df_receita['DATA'])

    # === Filtros ===
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

    # === Dados de 2024 ===
    df_filtrado['Ano'] = df_filtrado['DATA'].dt.year
    df_2024 = df_filtrado[df_filtrado['Ano'] == 2024]
    contas_filtradas_2024 = df_2024['Conta'].unique()
    auc_2024 = df_pl[df_pl['Conta'].isin(contas_filtradas_2024)]['PL Total'].sum()
    receita_2024 = df_2024['Receita Líquida'].sum()
    roa_total = (receita_2024 / auc_2024) * 100 if auc_2024 != 0 else 0

    # === Layout: Indicadores + Pizza ===
    col_kpis, col_pizza = st.columns([1, 2.5])

    auc_formatado = f"R$ {auc_2024:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    receita_formatada = f"R$ {receita_2024:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    roa_formatado = f"{roa_total:.2f}%".replace(".", ",") if pd.notnull(roa_total) else ""


    if not df_2024.empty:
        df_cat = df_2024.groupby('Categoria')['Receita Líquida'].sum().reset_index()
        categoria_total = df_cat['Receita Líquida'].sum()
        categoria_formatada = f"R$ {categoria_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        df_prod = df_2024.groupby('Produto')['Receita Líquida'].sum().reset_index()
        produto_total = df_prod['Receita Líquida'].sum()
        produto_formatado = f"R$ {produto_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        categoria_formatada = "Sem dados"
        produto_formatado = "Sem dados"


    # Título fora do card
    st.markdown("### 📌 Indicadores Gerais 2024")

    # Estilo do cartão individual
    card_style = """
    <div style='background-color: white; padding: 15px; margin-bottom: 12px;
                border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                border-left: 6px solid {color};'>
        <strong>{label}</strong><br> {value}
    </div>
    """

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown(card_style.format(label="AuC 2024", value=auc_formatado, color="#37cc84"), unsafe_allow_html=True)
    with col2:
        st.markdown(card_style.format(label="Receita 2024", value=receita_formatada, color="#67ff9a"), unsafe_allow_html=True)
    with col3:
        st.markdown(card_style.format(label="ROA 2024", value=roa_formatado, color="#37cc84"), unsafe_allow_html=True)
    

    df_roa = calcular_roa(df_filtrado, df_pl)

    st.subheader("📊 Receita Mensal")
    df_filtrado['Mes'] = df_filtrado['DATA'].dt.strftime('%b')
    traduzir_meses = {'Jan': 'Jan', 'Feb': 'Fev', 'Mar': 'Mar', 'Apr': 'Abr','May': 'Mai', 'Jun': 'Jun', 'Jul': 'Jul', 'Aug': 'Ago','Sep': 'Set', 'Oct': 'Out', 'Nov': 'Nov', 'Dec': 'Dez'}
    df_filtrado['Mes'] = df_filtrado['Mes'].map(traduzir_meses)
    ordem_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun','Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    receita_mensal = df_filtrado.groupby('Mes')['Receita Líquida'].sum().reindex(ordem_meses).fillna(0).reset_index()
    receita_mensal.columns = ['Mês', 'Receita']
    fig_receita = px.bar(
    receita_mensal, x='Mês', y='Receita',
    labels={'Receita': 'Receita Líquida (R$)'},
    text_auto='.2s',
    color_discrete_sequence=['#37cc84']
    )
    fig_receita.update_layout(
    yaxis_tickformat=',.2f',
    yaxis_title='Receita Líquida (R$)',
    xaxis_title='Mês',
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False)
    )
    fig_receita.update_yaxes(separatethousands=True)
    st.plotly_chart(fig_receita, use_container_width=True)

    st.subheader("📈 Evolução RoA")
    df_2024['MesNum'] = df_2024['DATA'].dt.month
    receita_mensal_roae = df_2024.groupby('MesNum')['Receita Líquida'].sum().reindex(range(1, 13)).fillna(0).reset_index()
    receita_mensal_roae['MesNome'] = receita_mensal_roae['MesNum'].map(dict(zip(range(1, 13), [month_abbr[i] for i in range(1, 13)])))
    acumulado, pontos_roae = 0, []
    for i, row in receita_mensal_roae.iterrows():
        acumulado += row['Receita Líquida']
        media = acumulado / (i + 1)
        roa_e = (media * 12) / auc_2024 * 100 if auc_2024 != 0 else 0
        pontos_roae.append(roa_e)
    x_labels = receita_mensal_roae['MesNome'].tolist() + ['Total 2024']
    y_roae = pontos_roae + [None]
    y_roa_bar = [None] * 12 + [roa_total]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
    x=x_labels, y=y_roae, mode='lines+markers+text', name='ROAE (%)', text=[f"{val:.2f}%" if val is not None else "" for val in y_roae],
    textposition="top center",
    line=dict(color='#37cc84'), marker=dict(color='#37cc84')
    ))
    fig.add_trace(go.Bar(
    x=x_labels, y=y_roa_bar, name='ROA Final (%)',
    marker_color='#37cc84', text=[f"{val:.2f}%" if val is not None else "" for val in y_roa_bar],
    textposition='outside'
    ))
    fig.update_layout(
    yaxis_tickformat=',.2f',
    yaxis_title='ROAE / ROA (%)',
    xaxis_title='Mês',
    xaxis=dict(type='category', showgrid=False),
    yaxis=dict(showgrid=False)
    )
    
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Planilha Geral")
    tabela_final = criar_tabela_receita_roa(df_filtrado, df_pl)
    tabela_formatada = tabela_final.copy()
    for col in ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez','Total 2024','AuC']:
        tabela_formatada[col] = tabela_formatada[col].map(lambda x: f"{x:,.2f}".replace(",","X").replace(".",", ").replace("X","."))
    tabela_formatada['ROA'] = pd.to_numeric(tabela_formatada['ROA'], errors='coerce')
    tabela_formatada['ROA'] = tabela_formatada['ROA'].map(lambda x: f"{x:,.2f}%".replace(",","X").replace(".",", ").replace("X",".") if pd.notnull(x) else "")
    tabela_formatada['ROA Referência'] = tabela_formatada['ROA Referência'].map(lambda x: f"{x:,.2f}%".replace(",","X").replace(".",", ").replace("X",".") if pd.notnull(x) else "")
    st.dataframe(tabela_formatada)
    csv_tabela = tabela_final.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Baixar Planilha Geral", data=csv_tabela, file_name="tabela_receita_roa.csv", mime="text/csv")

    st.subheader("📋 Planilha Geral - Elegíveis Fee Fixo (20% amplitude)")
    planilha_fee_fixo = tabela_final[
        (
            ((tabela_final['AuC'] >= 100000) & (tabela_final['AuC'] <= 1000000) & (tabela_final['ROA'] >= 0.80) & (tabela_final['ROA'] <= 1.20)) |
            ((tabela_final['AuC'] > 1000000) & (tabela_final['AuC'] <= 5000000) & (tabela_final['ROA'] >= 0.60) & (tabela_final['ROA'] <= 0.90)) |
            ((tabela_final['AuC'] > 5000000) & (tabela_final['AuC'] <= 10000000) & (tabela_final['ROA'] >= 0.48) & (tabela_final['ROA'] <= 0.72)) |
            ((tabela_final['AuC'] > 10000000) & (tabela_final['ROA'] >= 0.40) & (tabela_final['ROA'] <= 0.60))
        )
    ].copy()
    planilha_fee_fixo['ROA Referência'] = planilha_fee_fixo['AuC'].apply(calcular_roa_referencia)
    planilha_formatada = planilha_fee_fixo.copy()
    for col in ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez','Total 2024','AuC']:
        if col in planilha_formatada.columns:
            planilha_formatada[col] = planilha_formatada[col].map(lambda x: f"{x:,.2f}".replace(",","X").replace(".",", ").replace("X","."))
    planilha_formatada['ROA'] = planilha_formatada['ROA'].map(lambda x: f"{x:,.2f}%".replace(",","X").replace(".",", ").replace("X",".") if pd.notnull(x) else "")
    planilha_formatada['ROA Referência'] = planilha_formatada['ROA Referência'].map(lambda x: f"{x:,.2f}%".replace(",","X").replace(".",", ").replace("X",".") if pd.notnull(x) else "")
    st.dataframe(planilha_formatada)
    csv_fee_fixo = planilha_fee_fixo.to_csv(index=False).encode('utf-8')
    st.download_button("💾 Baixar Planilha Geral - Elegíveis Fee Fixo", data=csv_fee_fixo, file_name="planilha_fee_fixo.csv", mime="text/csv")

    # Adicione isso ao final do seu app.py, logo abaixo da "Planilha Geral - Fee Fixo"

    st.subheader("💡 Fee Fixo - Por Faixas")

    # Reaplica o cálculo da ROA Referência e Dif. ROA
    tabela_final['ROA Referência'] = tabela_final['AuC'].apply(calcular_roa_referencia)
    tabela_final['Dif. ROA'] = tabela_final['ROA'] - tabela_final['ROA Referência']

    # Função de formatação para as 4 tabelas
    def formatar_tabela_resumo(df):
        df_fmt = df[['Assessor Principal', 'Conta', 'AuC', 'ROA', 'ROA Referência', 'Dif. ROA']].copy()
        df_fmt['AuC'] = df_fmt['AuC'].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        df_fmt['ROA'] = df_fmt['ROA'].map(lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
        df_fmt['ROA Referência'] = df_fmt['ROA Referência'].map(lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
        df_fmt['Dif. ROA'] = df_fmt['Dif. ROA'].map(lambda x: f"{x:+,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."))
        return df_fmt

    # Tabelas por faixa com ordenação
    faixa1_tbl = tabela_final[(tabela_final['AuC'] >= 100000) & (tabela_final['AuC'] <= 1000000)].sort_values(by='ROA', ascending=False)
    faixa2_tbl = tabela_final[(tabela_final['AuC'] > 1000000) & (tabela_final['AuC'] <= 5000000)].sort_values(by='ROA', ascending=False)
    faixa3_tbl = tabela_final[(tabela_final['AuC'] > 5000000) & (tabela_final['AuC'] <= 10000000)].sort_values(by='ROA', ascending=False)
    faixa4_tbl = tabela_final[(tabela_final['AuC'] > 10000000)].sort_values(by='ROA', ascending=False)

    # Mostrar lado a lado
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("**Faixa 1 - AuC até 1mm**")
        df1_fmt = formatar_tabela_resumo(faixa1_tbl)
        st.dataframe(df1_fmt)
        csv1 = faixa1_tbl.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Baixar Faixa 1", data=csv1, file_name="faixa1.csv", mime="text/csv")
    with col_f2:
        st.markdown("**Faixa 2 - de 1mm a 5mm**")
        df2_fmt = formatar_tabela_resumo(faixa2_tbl)
        st.dataframe(df2_fmt)
        csv2 = faixa2_tbl.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Baixar Faixa 2", data=csv2, file_name="faixa2.csv", mime="text/csv")

    col_f3, col_f4 = st.columns(2)
    with col_f3:
        st.markdown("**Faixa 3 - de 5mm a 10mm**")
        df3_fmt = formatar_tabela_resumo(faixa3_tbl)
        st.dataframe(df3_fmt)
        csv3 = faixa3_tbl.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Baixar Faixa 3", data=csv3, file_name="faixa3.csv", mime="text/csv")
    with col_f4:
        st.markdown("**Faixa 4 - acima de 10 mm**")
        df4_fmt = formatar_tabela_resumo(faixa4_tbl)
        st.dataframe(df4_fmt)
        csv4 = faixa4_tbl.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Baixar Faixa 4", data=csv4, file_name="faixa4.csv", mime="text/csv")
