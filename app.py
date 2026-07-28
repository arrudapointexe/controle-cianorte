import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

st.set_page_config(page_title="Cianorte - Controle de Fluxo", page_icon="🛍️", layout="wide")

# Inicializa a conexão com o Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    connected = True
except Exception as e:
    connected = False
    st.error("⚠️ As credenciais do Google Sheets não foram encontradas. Siga o tutorial para configurar.")

def load_data():
    if connected:
        try:
            # ttl=0 garante que os dados estão sempre atualizados e não cacheados (bom para múltiplas lojas)
            df = conn.read(worksheet="Página1", ttl=0)
            
            # Se a planilha estiver vazia, cria a estrutura
            if df.empty or 'Data_Hora' not in df.columns:
                return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])
            return df
        except Exception as e:
            st.warning("⚠️ Planilha não encontrada ou vazia. Certifique-se de que compartilhou a planilha com o e-mail do bot.")
            return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])

def save_data(data):
    if connected:
        try:
            conn.update(worksheet="Página1", data=data)
            st.cache_data.clear() # Limpa o cache para que a próxima leitura venha atualizada
        except Exception as e:
            st.error(f"Erro ao salvar na nuvem: {e}")

def load_checklist():
    if connected:
        try:
            df = conn.read(worksheet="Checklist", ttl=0)
            if df.empty or 'Data_Hora' not in df.columns:
                return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
            return df
        except Exception as e:
            return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])

def save_checklist(data):
    if connected:
        try:
            conn.update(worksheet="Checklist", data=data)
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao salvar checklist: {e}")

def load_config():
    if connected:
        try:
            df = conn.read(worksheet="Config", ttl=0)
            if df.empty or 'Loja' not in df.columns:
                return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria"])
            return df
        except Exception as e:
            return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria"])
    else:
        return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria"])

# Sempre recarregar os dados do zero para evitar sobreposição se outra loja usou
st.session_state.data = load_data()
st.session_state.checklist_data = load_checklist()
st.session_state.config_data = load_config()

# Configuração de listas padrão
tarefas_checklist = ["Limpeza da loja", "Organização do estoque", "Reposição de vitrine", "Fechamento de caixa", "Conferência de provadores"]

# Prepara as lojas baseadas na configuração
df_config = st.session_state.config_data
if not df_config.empty and "Loja" in df_config.columns:
    lojas_disponiveis = df_config["Loja"].dropna().unique().tolist()
    if not lojas_disponiveis:
        lojas_disponiveis = ["Cianorte Matriz"]
else:
    lojas_disponiveis = ["Cianorte Matriz", "Cianorte Filial 1", "Cianorte Filial 2"]

# Estado para manter a loja selecionada salva usando query_params
params = st.query_params
loja_salva = params.get("loja", lojas_disponiveis[0])

if "loja_selecionada" not in st.session_state or st.session_state.loja_selecionada not in lojas_disponiveis:
    st.session_state.loja_selecionada = loja_salva if loja_salva in lojas_disponiveis else lojas_disponiveis[0]

# Define funcionárias para a loja atual
if not df_config.empty and "Nome_Funcionaria" in df_config.columns:
    df_func = df_config[df_config["Loja"] == st.session_state.loja_selecionada].dropna(subset=["Nome_Funcionaria"])
    funcionarias_disponiveis = []
    for _, row in df_func.iterrows():
        nome = str(row['Nome_Funcionaria']).strip()
        if not nome or nome.lower() == "nan":
            continue
        codigo = str(row['Codigo_Funcionaria']).replace('.0', '').strip() if 'Codigo_Funcionaria' in row and pd.notna(row['Codigo_Funcionaria']) else ""
        
        if codigo and codigo.lower() != "nan":
            funcionarias_disponiveis.append(f"{codigo} - {nome}")
        else:
            funcionarias_disponiveis.append(nome)
            
    if not funcionarias_disponiveis:
        funcionarias_disponiveis = ["(Sem funcionárias cadastradas)"]
else:
    funcionarias_disponiveis = ["Ana", "Beatriz", "Carlos", "Diana"]

st.title("🛍️ Controle de Fluxo - Lojas Cianorte")

if not connected:
    st.info("Aguardando configuração do Google Sheets... Siga o passo a passo enviado.")

# Criação das abas
aba_vendedoras, aba_checklist, aba_admin = st.tabs(["👩‍💼 Área das Vendedoras", "✅ Checklist Diário", "📊 Área Administrativa"])

with aba_vendedoras:
    st.header("Registro de Movimentação")
    
    index_atual = lojas_disponiveis.index(st.session_state.loja_selecionada) if st.session_state.loja_selecionada in lojas_disponiveis else 0
    loja = st.selectbox("📍 Selecione sua Loja:", lojas_disponiveis, index=index_atual)
    
    if loja != st.session_state.loja_selecionada:
        st.session_state.loja_selecionada = loja
        st.query_params.loja = loja
        st.rerun()
    
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
                "Observacoes": "-",
                "Funcionaria": "-"
            }
            # Concatena o novo registro e salva
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(st.session_state.data)
            st.success(f"Entrada registrada para {loja}!")
            
    with col_saida:
        st.subheader("🔴 Saída de Cliente")
        st.markdown("Preencha ao cliente sair da loja.")
        
        with st.form("form_saida", clear_on_submit=True):
            funcionaria = st.selectbox("Quem está registrando?", ["Selecione"] + funcionarias_disponiveis)
            
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
                if funcionaria == "Selecione":
                    st.error("Por favor, selecione quem está registrando a saída.")
                elif purchased == "Não" and reason == "":
                    st.error("Por favor, informe o motivo da não compra.")
                else:
                    new_entry = {
                        "Data_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Loja": loja,
                        "Tipo_Evento": "Saida",
                        "Comprou": purchased,
                        "Motivo_Nao_Compra": reason if purchased == "Não" else "-",
                        "Observacoes": notes,
                        "Funcionaria": funcionaria
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(st.session_state.data)
                    st.success(f"Saída registrada para {loja}!")

with aba_checklist:
    st.header(f"✅ Checklist Diário - {st.session_state.loja_selecionada}")
    st.markdown("Marque as tarefas concluídas hoje.")
    
    hoje_str = datetime.now().strftime("%Y-%m-%d")
    df_check = st.session_state.checklist_data
    
    # Filtra as tarefas de hoje para a loja atual
    if not df_check.empty:
        # Pega os primeiros 10 caracteres da Data_Hora para comparar com hoje_str
        df_hoje = df_check[df_check["Data_Hora"].str[:10] == hoje_str]
        df_loja_hoje = df_hoje[df_hoje["Loja"] == st.session_state.loja_selecionada]
    else:
        df_loja_hoje = pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
        
    tarefas_concluidas_hoje = df_loja_hoje[df_loja_hoje["Status"] == "Concluído"]["Tarefa"].tolist()
    
    with st.form("form_checklist", clear_on_submit=True):
        funcionaria_check = st.selectbox("Quem está preenchendo?", ["Selecione"] + funcionarias_disponiveis)
        
        novas_conclusoes = []
        for tarefa in tarefas_checklist:
            ja_concluida = tarefa in tarefas_concluidas_hoje
            if ja_concluida:
                st.checkbox(f"~~{tarefa}~~ (Já concluído)", value=True, disabled=True)
            else:
                marcou = st.checkbox(tarefa)
                if marcou:
                    novas_conclusoes.append(tarefa)
                    
        submit_check = st.form_submit_button("Salvar Checklist", use_container_width=True)
        
        if submit_check:
            if funcionaria_check == "Selecione" and len(novas_conclusoes) > 0:
                st.error("Por favor, selecione quem está preenchendo antes de salvar.")
            elif len(novas_conclusoes) > 0:
                novos_registros = []
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for tarefa_nova in novas_conclusoes:
                    novos_registros.append({
                        "Data_Hora": agora,
                        "Loja": st.session_state.loja_selecionada,
                        "Funcionaria": funcionaria_check,
                        "Tarefa": tarefa_nova,
                        "Status": "Concluído"
                    })
                
                st.session_state.checklist_data = pd.concat([st.session_state.checklist_data, pd.DataFrame(novos_registros)], ignore_index=True)
                save_checklist(st.session_state.checklist_data)
                st.success(f"{len(novas_conclusoes)} tarefa(s) salva(s) com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma nova tarefa foi marcada.")

with aba_admin:
    st.header("Visão Geral das Lojas")
    
    df = st.session_state.data
    
    if not df.empty and connected:
        df['Data'] = df['Data_Hora'].str[:10]
        hoje = datetime.now().strftime("%Y-%m-%d")
        df_hoje = df[df['Data'] == hoje]
        
        st.subheader(f"📅 Dados de Hoje ({hoje})")
        
        cols = st.columns(len(lojas_disponiveis))
        
        for i, nome_loja in enumerate(lojas_disponiveis):
            df_loja = df_hoje[df_hoje["Loja"] == nome_loja]
            
            entradas = len(df_loja[df_loja["Tipo_Evento"] == "Entrada"])
            saidas = len(df_loja[df_loja["Tipo_Evento"] == "Saida"])
            
            clientes_na_loja = max(0, entradas - saidas)
            
            vendas = len(df_loja[(df_loja["Tipo_Evento"] == "Saida") & (df_loja["Comprou"] == "Sim")])
            
            taxa_conversao = (vendas / saidas * 100) if saidas > 0 else 0
            
            with cols[i]:
                st.markdown(f"### {nome_loja}")
                
                st.metric("Pessoas na Loja Agora", clientes_na_loja, delta=None)
                
                st.markdown("**Resumo do Dia:**")
                st.write(f"- **Entradas:** {entradas}")
                st.write(f"- **Saídas:** {saidas}")
                st.write(f"- **Vendas (Conversão):** {vendas} vendas")
                
                st.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%")
                
                st.divider()
        
        st.subheader("📋 Registros Recentes (Todas as Lojas)")
        st.dataframe(
            df.tail(15).sort_values(by="Data_Hora", ascending=False).drop(columns=['Data'], errors='ignore'), 
            use_container_width=True
        )
        
    else:
        st.info("Nenhum dado registrado ainda ou sem conexão.")
