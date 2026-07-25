import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Novo arquivo para lidar com a estrutura de Entradas/Saídas separadas
DATA_FILE = "dados_loja_v2.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes"])

def save_data(data):
    data.to_csv(DATA_FILE, index=False)

st.set_page_config(page_title="Cianorte - Controle de Fluxo", page_icon="🛍️", layout="wide")

if "data" not in st.session_state:
    st.session_state.data = load_data()

# Estado para manter a loja selecionada salva
if "loja_selecionada" not in st.session_state:
    st.session_state.loja_selecionada = "Cianorte Matriz"

lojas_disponiveis = ["Cianorte Matriz", "Cianorte Filial 1", "Cianorte Filial 2"]

st.title("🛍️ Controle de Fluxo - Lojas Cianorte")

# Criação das abas
aba_vendedoras, aba_admin = st.tabs(["👩‍💼 Área das Vendedoras", "📊 Área Administrativa"])

with aba_vendedoras:
    st.header("Registro de Movimentação")
    
    # Seletor de loja fica FORA do formulário, assim ele não reseta quando algo for enviado
    index_atual = lojas_disponiveis.index(st.session_state.loja_selecionada) if st.session_state.loja_selecionada in lojas_disponiveis else 0
    loja = st.selectbox("📍 Selecione sua Loja:", lojas_disponiveis, index=index_atual)
    
    # Atualiza a loja no session state para a próxima vez que a tela carregar
    st.session_state.loja_selecionada = loja
    
    st.divider()
    
    col_entrada, col_saida = st.columns(2)
    
    with col_entrada:
        st.subheader("🟢 Entrada de Cliente")
        st.markdown("Clique abaixo quando um cliente entrar na loja.")
        
        if st.button("Registrar Nova Entrada", use_container_width=True, type="primary"):
            new_entry = {
                "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Loja": loja,
                "Tipo_Evento": "Entrada",
                "Comprou": "-",
                "Motivo_Nao_Compra": "-",
                "Observacoes": "-"
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(st.session_state.data)
            st.success(f"Entrada registrada para {loja}!")
            
    with col_saida:
        st.subheader("🔴 Saída de Cliente")
        st.markdown("Preencha ao cliente sair da loja.")
        
        with st.form("form_saida", clear_on_submit=True):
            purchased = st.radio("O cliente realizou uma compra?", ("Sim", "Não"), horizontal=True)
            
            reason = st.selectbox("Motivo da não compra (Preencha apenas se 'Não')", [
                "",
                "Só estava olhando",
                "Achou caro",
                "Não encontrou o que procurava",
                "Falta de tamanho/cor",
                "Mau atendimento",
                "Problema na forma de pagamento",
                "Outro"
            ])
            
            notes = st.text_area("Observações (opcional)")
            
            submit_saida = st.form_submit_button("Registrar Saída", use_container_width=True)
            
            if submit_saida:
                if purchased == "Não" and reason == "":
                    st.error("Por favor, informe o motivo da não compra.")
                else:
                    new_entry = {
                        "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Loja": loja,
                        "Tipo_Evento": "Saida",
                        "Comprou": purchased,
                        "Motivo_Nao_Compra": reason if purchased == "Não" else "-",
                        "Observacoes": notes
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.success(f"Saída registrada para {loja}!")

with aba_admin:
    st.header("Visão Geral das Lojas")
    
    df = st.session_state.data
    
    if not df.empty:
        # Prepara a coluna de Data para filtrar apenas hoje
        df['Data'] = df['Data_Hora'].str[:10]
        hoje = datetime.now().strftime("%Y-%m-%d")
        df_hoje = df[df['Data'] == hoje]
        
        st.subheader(f"📅 Dados de Hoje ({hoje})")
        
        # Cria colunas iguais à quantidade de lojas
        cols = st.columns(len(lojas_disponiveis))
        
        for i, nome_loja in enumerate(lojas_disponiveis):
            df_loja = df_hoje[df_hoje["Loja"] == nome_loja]
            
            entradas = len(df_loja[df_loja["Tipo_Evento"] == "Entrada"])
            saidas = len(df_loja[df_loja["Tipo_Evento"] == "Saida"])
            
            # Para evitar número negativo caso esqueçam de bater entrada
            clientes_na_loja = max(0, entradas - saidas)
            
            vendas = len(df_loja[(df_loja["Tipo_Evento"] == "Saida") & (df_loja["Comprou"] == "Sim")])
            
            # A conversão agora é calculada sobre a base de saídas
            taxa_conversao = (vendas / saidas * 100) if saidas > 0 else 0
            
            with cols[i]:
                st.markdown(f"### {nome_loja}")
                
                st.metric("Pessoas na Loja Agora", clientes_na_loja, delta=None)
                
                st.markdown("**Resumo do Dia:**")
                st.write(f"- **Entradas:** {entradas}")
                st.write(f"- **Saídas:** {saidas}")
                st.write(f"- **Vendas (Conversão):** {vendas} vendas")
                
                # Exibir a taxa em destaque
                st.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%")
                
                st.divider()
        
        st.subheader("📋 Registros Recentes (Todas as Lojas)")
        st.dataframe(
            df.tail(15).sort_values(by="Data_Hora", ascending=False).drop(columns=['Data'], errors='ignore'), 
            use_container_width=True
        )
        
    else:
        st.info("Nenhum dado registrado ainda.")
