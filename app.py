import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
import os
import urllib.parse

st.set_page_config(page_title="Cianorte - Controle de Fluxo", page_icon="🛍️", layout="wide")

def get_now():
    return datetime.now() - timedelta(hours=3)

# Inicializa a conexão com o PostgreSQL
try:
    conn = st.connection("postgresql", type="sql")
    connected = True
except Exception as e:
    connected = False
    st.error(f"⚠️ As credenciais do banco de dados não foram configuradas corretamente. Erro: {e}")

def load_data():
    if connected:
        try:
            # ttl=0 garante que os dados estão sempre atualizados e não cacheados
            df = conn.query("SELECT * FROM eventos ORDER BY id ASC", ttl=0)
            if df.empty:
                return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])
            
            # Garante que dados históricos fiquem em uppercase
            if "Funcionaria" in df.columns:
                df["Funcionaria"] = df["Funcionaria"].str.upper()
                
            return df
        except Exception as e:
            st.warning(f"⚠️ Tabela de eventos não encontrada ou vazia. {e}")
            return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria"])

def insert_evento(entry):
    if connected:
        try:
            with conn.session as s:
                s.execute(
                    text('INSERT INTO eventos ("Data_Hora", "Loja", "Tipo_Evento", "Comprou", "Motivo_Nao_Compra", "Observacoes", "Funcionaria") VALUES (:Data_Hora, :Loja, :Tipo_Evento, :Comprou, :Motivo_Nao_Compra, :Observacoes, :Funcionaria)'),
                    entry
                )
                s.commit()
            st.cache_data.clear() # Limpa o cache para que a próxima leitura venha atualizada
        except Exception as e:
            st.error(f"Erro ao salvar no banco de dados: {e}")

def load_checklist():
    if connected:
        try:
            df = conn.query("SELECT * FROM checklists ORDER BY id ASC", ttl=0)
            if df.empty:
                return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
            
            # Garante que dados históricos fiquem em uppercase
            if "Funcionaria" in df.columns:
                df["Funcionaria"] = df["Funcionaria"].str.upper()
                
            return df
        except Exception as e:
            return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])

def insert_checklists(entries):
    if connected:
        try:
            with conn.session as s:
                for entry in entries:
                    s.execute(
                        text('INSERT INTO checklists ("Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status") VALUES (:Data_Hora, :Loja, :Funcionaria, :Tarefa, :Status)'),
                        entry
                    )
                s.commit()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao salvar checklist: {e}")

def load_config():
    if connected:
        try:
            df = conn.query("SELECT * FROM configs ORDER BY id ASC", ttl=0)
            if df.empty:
                return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria", "Tarefa_Checklist"])
            return df
        except Exception as e:
            return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria", "Tarefa_Checklist"])
    else:
        return pd.DataFrame(columns=["Loja", "Codigo_Funcionaria", "Nome_Funcionaria", "Tarefa_Checklist"])

# NOVA FUNÇÃO PARA CARREGAR OS DADOS DO WHATSAPP
def load_whatsapp():
    if connected:
        try:
            df = conn.query("SELECT * FROM clientes_whatsapp ORDER BY id ASC", ttl=0)
            if df.empty:
                return pd.DataFrame(columns=["Data_Hora", "Loja", "Nome_Cliente", "Telefone", "Motivo_Contato", "Objetivo_Reenvio", "Observacoes", "Funcionaria", "Status_Contato"])
            
            if "Funcionaria" in df.columns:
                df["Funcionaria"] = df["Funcionaria"].str.upper()
                
            return df
        except Exception as e:
            st.warning(f"⚠️ Tabela de clientes_whatsapp não encontrada. Não esqueça de criá-la no banco. {e}")
            return pd.DataFrame(columns=["Data_Hora", "Loja", "Nome_Cliente", "Telefone", "Motivo_Contato", "Objetivo_Reenvio", "Observacoes", "Funcionaria", "Status_Contato"])
    else:
        return pd.DataFrame(columns=["Data_Hora", "Loja", "Nome_Cliente", "Telefone", "Motivo_Contato", "Objetivo_Reenvio", "Observacoes", "Funcionaria", "Status_Contato"])

# NOVA FUNÇÃO PARA INSERIR OS DADOS DO WHATSAPP
def insert_whatsapp(entry):
    if connected:
        try:
            with conn.session as s:
                s.execute(
                    text('INSERT INTO clientes_whatsapp ("Data_Hora", "Loja", "Nome_Cliente", "Telefone", "Motivo_Contato", "Objetivo_Reenvio", "Observacoes", "Funcionaria", "Status_Contato") VALUES (:Data_Hora, :Loja, :Nome_Cliente, :Telefone, :Motivo_Contato, :Objetivo_Reenvio, :Observacoes, :Funcionaria, :Status_Contato)'),
                    entry
                )
                s.commit()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Erro ao salvar no banco de dados (WhatsApp): {e}")

# Sempre recarregar os dados do zero para evitar sobreposição se outra loja usou
st.session_state.data = load_data()
st.session_state.checklist_data = load_checklist()
st.session_state.config_data = load_config()
st.session_state.whatsapp_data = load_whatsapp() # Carregando estado do WhatsApp

# Prepara as lojas baseadas na configuração
df_config = st.session_state.config_data

# Configuração do Checklist
if not df_config.empty and "Tarefa_Checklist" in df_config.columns:
    tarefas_checklist = df_config["Tarefa_Checklist"].dropna().astype(str).unique().tolist()
    tarefas_checklist = list(dict.fromkeys([t.strip() for t in tarefas_checklist if t.strip() != ""]))
    if not tarefas_checklist:
        tarefas_checklist = ["Limpeza da loja", "Organização do estoque", "Reposição de vitrine", "Fechamento de caixa", "Conferência de provadores"]
else:
    tarefas_checklist = ["Limpeza da loja", "Organização do estoque", "Reposição de vitrine", "Fechamento de caixa", "Conferência de provadores"]

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
    st.info("Aguardando configuração do PostgreSQL... Verifique as credenciais.")

# Criação das abas
aba_vendedoras, aba_checklist, aba_whatsapp, aba_admin = st.tabs([
    "👩‍💼 Área das Vendedoras", 
    "✅ Checklist Diário", 
    "📱 Clientes WhatsApp", 
    "📊 Área Administrativa"
])

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
                "Data_Hora": get_now().strftime("%Y-%m-%d %H:%M:%S"),
                "Loja": loja,
                "Tipo_Evento": "Entrada",
                "Comprou": "-",
                "Motivo_Nao_Compra": "-",
                "Observacoes": "-",
                "Funcionaria": "-"
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
            insert_evento(new_entry)
            st.success(f"Entrada registrada para {loja}!")
            
    with col_saida:
        st.subheader("🔴 Saída de Cliente")
        st.markdown("Preencha ao cliente sair da loja.")
        
        with st.form("form_saida", clear_on_submit=True):
            funcionaria = st.text_input("Nome da funcionária atendendo")
            
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
                if not funcionaria.strip():
                    st.error("Por favor, digite o nome de quem está registrando a saída.")
                elif purchased == "Não" and reason == "":
                    st.error("Por favor, informe o motivo da não compra.")
                else:
                    new_entry = {
                        "Data_Hora": get_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Loja": loja,
                        "Tipo_Evento": "Saida",
                        "Comprou": purchased,
                        "Motivo_Nao_Compra": reason if purchased == "Não" else "-",
                        "Observacoes": notes,
                        "Funcionaria": funcionaria.strip().upper()
                    }
                    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True)
                    insert_evento(new_entry)
                    st.success(f"Saída registrada para {loja}!")

with aba_checklist:
    st.header(f"✅ Checklist Diário - {st.session_state.loja_selecionada}")
    st.markdown("Marque as tarefas concluídas hoje. *(O dia reinicia às 8h da manhã)*")
    
    logical_date = (get_now() - timedelta(hours=8)).strftime("%Y-%m-%d")
    df_check = st.session_state.checklist_data
    
    if not df_check.empty:
        df_check['Data_Logica'] = pd.to_datetime(df_check['Data_Hora'], format="%Y-%m-%d %H:%M:%S", errors='coerce').apply(lambda x: (x - timedelta(hours=8)).strftime("%Y-%m-%d") if pd.notna(x) else "")
        df_hoje = df_check[df_check["Data_Logica"] == logical_date]
        df_loja_hoje = df_hoje[df_hoje["Loja"] == st.session_state.loja_selecionada]
    else:
        df_loja_hoje = pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
        
    tarefas_concluidas_hoje = df_loja_hoje[df_loja_hoje["Status"] == "Concluído"]["Tarefa"].tolist()
    
    with st.form("form_checklist", clear_on_submit=True):
        funcionaria_check = st.text_input("Nome da funcionária")
        
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
            if not funcionaria_check.strip() and len(novas_conclusoes) > 0:
                st.error("Por favor, digite quem está preenchendo antes de salvar.")
            elif len(novas_conclusoes) > 0:
                novos_registros = []
                agora = get_now().strftime("%Y-%m-%d %H:%M:%S")
                for tarefa_nova in novas_conclusoes:
                    novos_registros.append({
                        "Data_Hora": agora,
                        "Loja": st.session_state.loja_selecionada,
                        "Funcionaria": funcionaria_check.strip().upper(),
                        "Tarefa": tarefa_nova,
                        "Status": "Concluído"
                    })
                
                st.session_state.checklist_data = pd.concat([st.session_state.checklist_data, pd.DataFrame(novos_registros)], ignore_index=True)
                insert_checklists(novos_registros)
                st.success(f"{len(novas_conclusoes)} tarefa(s) salva(s) com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma nova tarefa foi marcada.")

# NOVA ABA: CLIENTES WHATSAPP
with aba_whatsapp:
    st.header(f"📱 Clientes WhatsApp - {st.session_state.loja_selecionada}")
    st.markdown("Registre clientes que enviaram mensagem para acompanhamento futuro (satisfação, compra ou recompra).")
    
    col_form, col_lista = st.columns([1, 1.5])
    
    with col_form:
        st.subheader("Novo Registro de Contato")
        with st.form("form_whatsapp", clear_on_submit=True):
            nome_cliente = st.text_input("Nome do Cliente*")
            telefone_cliente = st.text_input("Telefone / WhatsApp*")
            
            motivo_contato = st.selectbox("Motivo do Contato Original", [
                "Informação", 
                "Orçamento", 
                "Dúvida sobre Produto",
                "Reclamação", 
                "Outro"
            ])
            
            objetivo_reenvio = st.selectbox("Objetivo de Reenvio Futuro*", [
                "Satisfação (Pós-venda)", 
                "Tentativa de Compra (Não finalizou)", 
                "Recompra (Ofertas futuras)"
            ])
            
            obs_whats = st.text_area("Observações (O que o cliente queria?)")
            
            funcionaria_whats = st.text_input("Sua assinatura (Nome da funcionária)*")
            
            submit_whats = st.form_submit_button("Salvar Contato", use_container_width=True)
            
            if submit_whats:
                if not nome_cliente.strip() or not telefone_cliente.strip() or not funcionaria_whats.strip():
                    st.error("Por favor, preencha todos os campos obrigatórios (*).")
                else:
                    new_entry = {
                        "Data_Hora": get_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Loja": st.session_state.loja_selecionada,
                        "Nome_Cliente": nome_cliente.strip(),
                        "Telefone": telefone_cliente.strip(),
                        "Motivo_Contato": motivo_contato,
                        "Objetivo_Reenvio": objetivo_reenvio,
                        "Observacoes": obs_whats.strip(),
                        "Funcionaria": funcionaria_whats.strip().upper(),
                        "Status_Contato": "Pendente"
                    }
                    st.session_state.whatsapp_data = pd.concat([st.session_state.whatsapp_data, pd.DataFrame([new_entry])], ignore_index=True)
                    insert_whatsapp(new_entry)
                    st.success(f"Contato salvo com sucesso!")
                    
    with col_lista:
        st.subheader("📋 Lista de Contatos da Loja")
        df_whats = st.session_state.whatsapp_data
        
        if not df_whats.empty:
            df_loja_whats = df_whats[df_whats["Loja"] == st.session_state.loja_selecionada]
            if not df_loja_whats.empty:
                df_loja_whats = df_loja_whats.sort_values(by="Data_Hora", ascending=False)
                
                                for idx, row in df_loja_whats.iterrows():
                    icone = "🟢" if row.get("Status_Contato", "Pendente") == "Pendente" else "✅"
                    # CORREÇÃO DA DATA: coloquei o str() em volta do row['Data_Hora'] para não dar erro
                    with st.expander(f"{icone} {row['Nome_Cliente']} - {row['Objetivo_Reenvio']} ({str(row['Data_Hora'])[:10]})"):
                        st.write(f"**Telefone:** {row['Telefone']}")
                        st.write(f"**Motivo Inicial:** {row['Motivo_Contato']}")
                        st.write(f"**Observações:** {row['Observacoes']}")
                        st.write(f"**Atendido por:** {row['Funcionaria']}")
                        
                        # Definir mensagens padrão baseadas no objetivo (Decoradas e sem nome da loja)
                        nome_cliente = str(row['Nome_Cliente']).split(" ")[0].title()
                        func = str(row['Funcionaria']).capitalize()
                        objetivo = str(row['Objetivo_Reenvio'])
                        
                        if objetivo == "Satisfação (Pós-venda)":
                            msg = f"Oii {nome_cliente}, tudo bem maravilhosa? ✨ Aqui é a {func} da Cianorte! Passando pra saber se você amou as suas escolhas e se deu tudo certinho com as peças! 💖 Qualquer dúvida, estou super à disposição! Um beijo! 😘🛍️"
                        elif objetivo == "Tentativa de Compra (Não finalizou)":
                            msg = f"Oii {nome_cliente}, tudo bem flor? 🌸 Aqui é a {func} da Cianorte! Lembrei de você porque recebemos umas novidades MARAVILHOSAS na loja! 🤩✨ Como você estava olhando umas peças com a gente, pensei em te mandar algumas opções exclusivas que acabaram de chegar! Posso te mostrar sem compromisso? Tenho certeza que você vai amar! 💖👗"
                        elif objetivo == "Recompra (Ofertas futuras)":
                            msg = f"Oii {nome_cliente}, como você está? ✨ Aqui é a {func} da Cianorte! Passando pra te dar em primeira mão uma super novidade: estamos com peças lindíssimas e promoções imperdíveis que são a SUA cara! 😍🛍️ Posso te mandar algumas fotos pra você conferir? Preparamos tudo com muito carinho! ❤️✨"
                        else:
                            msg = f"Oii {nome_cliente}, tudo bem maravilhosa? ✨ Aqui é a {func} da Cianorte! 💖"
                            
                        st.write(f"**Sugestão de Mensagem:**")
                        st.code(msg, language="text")
                        
                        # Link para chamar no whatsapp
                        numero_limpo = ''.join(filter(str.isdigit, str(row['Telefone'])))
                        if numero_limpo:
                            # Se não tiver DDI, coloca 55 (Brasil) por padrão para facilitar
                            if len(numero_limpo) <= 11:
                                numero_limpo = "55" + numero_limpo
                                
                            msg_encoded = urllib.parse.quote(msg)
                            link_whats = f"https://wa.me/{numero_limpo}?text={msg_encoded}"
                            st.markdown(f"[💬 Chamar no WhatsApp com a mensagem pronta]({link_whats})")
            else:
                st.info("Nenhum contato registrado para esta loja.")
        else:
            st.info("Nenhum contato registrado.")

with aba_admin:
    st.header("Visão Geral das Lojas")
    
    df = st.session_state.data
    
    if not df.empty and connected:
        df['Data_Hora'] = pd.to_datetime(df['Data_Hora'], errors='coerce')
        df['Data'] = df['Data_Hora'].dt.strftime('%Y-%m-%d')
        df['Data_Date'] = df['Data_Hora'].dt.date
        
        col_filtro_data, col_calendario, col_filtro_loja = st.columns([1, 1, 1])
        
        with col_filtro_data:
            filtro_periodo = st.selectbox(
                "📅 Selecione o Período:", 
                ["Hoje", "Ontem", "Últimos 7 dias", "Mês Atual", "Período Personalizado", "Tudo"]
            )
            
        with col_filtro_loja:
            # Lista as lojas e adiciona a opção de ver todas
            opcoes_loja_admin = ["Todas as Lojas"] + lojas_disponiveis
            loja_selecionada_admin = st.selectbox("📍 Filtrar por Loja:", opcoes_loja_admin)
            
        hoje = get_now().date()
        
        # 1. Filtro de Data
        if filtro_periodo == "Hoje":
            df_filtrado = df[df['Data_Date'] == hoje]
        elif filtro_periodo == "Ontem":
            df_filtrado = df[df['Data_Date'] == (hoje - timedelta(days=1))]
        elif filtro_periodo == "Últimos 7 dias":
            df_filtrado = df[df['Data_Date'] >= (hoje - timedelta(days=7))]
        elif filtro_periodo == "Mês Atual":
            df_filtrado = df[(df['Data_Date'].apply(lambda x: x.month if pd.notna(x) else -1) == hoje.month) & 
                             (df['Data_Date'].apply(lambda x: x.year if pd.notna(x) else -1) == hoje.year)]
        elif filtro_periodo == "Período Personalizado":
            with col_calendario:
                datas_selecionadas = st.date_input(
                    "Selecione o intervalo (Início - Fim):",
                    value=(hoje - timedelta(days=7), hoje),
                    max_value=hoje,
                    format="DD/MM/YYYY"
                )
            if len(datas_selecionadas) == 2:
                data_inicio, data_fim = datas_selecionadas
                df_filtrado = df[(df['Data_Date'] >= data_inicio) & (df['Data_Date'] <= data_fim)]
            else:
                df_filtrado = df[df['Data_Date'] == datas_selecionadas[0]]
        else:
            df_filtrado = df
            
        # 2. Filtro de Loja
        if loja_selecionada_admin != "Todas as Lojas":
            df_filtrado = df_filtrado[df_filtrado["Loja"] == loja_selecionada_admin]
            lojas_para_exibir = [loja_selecionada_admin]
        else:
            lojas_para_exibir = lojas_disponiveis
            
        st.divider()
        st.subheader("🏆 Destaques do Período")
        
        if not df_filtrado.empty:
            loja_entradas = {}
            loja_conversao = {}
            
            for loja_nome in lojas_para_exibir:
                df_l = df_filtrado[df_filtrado["Loja"] == loja_nome]
                e = len(df_l[df_l["Tipo_Evento"] == "Entrada"])
                s = len(df_l[df_l["Tipo_Evento"] == "Saida"])
                v = len(df_l[(df_l["Tipo_Evento"] == "Saida") & (df_l["Comprou"] == "Sim")])
                loja_entradas[loja_nome] = e
                loja_conversao[loja_nome] = (v / s * 100) if s > 0 else 0
                
            df_nao_compra = df_filtrado[(df_filtrado["Tipo_Evento"] == "Saida") & (df_filtrado["Comprou"] == "Não")]
            if not df_nao_compra.empty:
                motivos_validos = df_nao_compra["Motivo_Nao_Compra"].replace(["-", ""], pd.NA).dropna()
                if not motivos_validos.empty:
                    maior_ofensor = motivos_validos.mode()[0]
                    ofensor_count = motivos_validos.value_counts().iloc[0]
                else:
                    maior_ofensor = "N/A"
                    ofensor_count = 0
            else:
                maior_ofensor = "Nenhum"
                ofensor_count = 0
                
            maior_fluxo_loja = max(loja_entradas, key=loja_entradas.get) if loja_entradas else "N/A"
            maior_conv_loja = max(loja_conversao, key=loja_conversao.get) if loja_conversao else "N/A"
            
            col_m1, col_m2, col_m3 = st.columns(3)
            
            # Dinâmica do Card: Se for todas as lojas mostra a "Vencedora", se for 1 loja, mostra o valor dela.
            if loja_selecionada_admin == "Todas as Lojas":
                col_m1.metric("🏆 Maior Conversão (Loja)", f"{maior_conv_loja}", f"{loja_conversao.get(maior_conv_loja, 0):.1f}%")
                col_m2.metric("👥 Maior Fluxo (Loja)", f"{maior_fluxo_loja}", f"{loja_entradas.get(maior_fluxo_loja, 0)} entradas")
            else:
                col_m1.metric("🏆 Taxa de Conversão", f"{loja_selecionada_admin}", f"{loja_conversao.get(loja_selecionada_admin, 0):.1f}%")
                col_m2.metric("👥 Fluxo Total", f"{loja_selecionada_admin}", f"{loja_entradas.get(loja_selecionada_admin, 0)} entradas")
                
            col_m3.metric("⚠️ Principal Motivo de Perda", f"{maior_ofensor}", f"{ofensor_count} vezes")
        else:
            st.info(f"Não há dados suficientes para os filtros selecionados.")
            
        st.divider()
        st.subheader(f"📊 Detalhamento por Loja ({filtro_periodo})")
        
        # Ajusta as colunas caso seja apenas uma loja selecionada
        num_cols = len(lojas_para_exibir) if len(lojas_para_exibir) > 0 else 1
        cols = st.columns(num_cols)
        
        df_hoje_real = df[df['Data_Date'] == hoje]
        
        for i, nome_loja in enumerate(lojas_para_exibir):
            df_loja_filtrado = df_filtrado[df_filtrado["Loja"] == nome_loja]
            df_loja_hoje = df_hoje_real[df_hoje_real["Loja"] == nome_loja]
            
            entradas_hoje = len(df_loja_hoje[df_loja_hoje["Tipo_Evento"] == "Entrada"])
            saidas_hoje = len(df_loja_hoje[df_loja_hoje["Tipo_Evento"] == "Saida"])
            clientes_na_loja = max(0, entradas_hoje - saidas_hoje)
            
            entradas = len(df_loja_filtrado[df_loja_filtrado["Tipo_Evento"] == "Entrada"])
            saidas = len(df_loja_filtrado[df_loja_filtrado["Tipo_Evento"] == "Saida"])
            vendas = len(df_loja_filtrado[(df_loja_filtrado["Tipo_Evento"] == "Saida") & (df_loja_filtrado["Comprou"] == "Sim")])
            taxa_conversao = (vendas / saidas * 100) if saidas > 0 else 0
            
            with cols[i]:
                st.markdown(f"### {nome_loja}")
                st.metric("Pessoas na Loja (AGORA)", clientes_na_loja, delta=None)
                
                st.markdown(f"**Resumo ({filtro_periodo}):**")
                st.write(f"- **Entradas:** {entradas}")
                st.write(f"- **Saídas:** {saidas}")
                st.write(f"- **Vendas:** {vendas}")
                st.metric("Taxa de Conversão", f"{taxa_conversao:.1f}%")
                if loja_selecionada_admin == "Todas as Lojas":
                    st.divider()
        
        st.divider()
        st.subheader("📋 Tarefas Pendentes do Checklist (Hoje)")
        
        df_check_admin = st.session_state.checklist_data
        logical_date_admin = (get_now() - timedelta(hours=8)).strftime("%Y-%m-%d")
        
        if not df_check_admin.empty:
            df_check_admin['Data_Logica'] = pd.to_datetime(df_check_admin['Data_Hora'], format="%Y-%m-%d %H:%M:%S", errors='coerce').apply(lambda x: (x - timedelta(hours=8)).strftime("%Y-%m-%d") if pd.notna(x) else "")
            df_check_hoje_admin = df_check_admin[df_check_admin["Data_Logica"] == logical_date_admin]
        else:
            df_check_hoje_admin = pd.DataFrame(columns=["Data_Hora", "Loja", "Funcionaria", "Tarefa", "Status"])
            
        cols_check = st.columns(num_cols)
        for i, nome_loja in enumerate(lojas_para_exibir):
            df_loja_check = df_check_hoje_admin[df_check_hoje_admin["Loja"] == nome_loja]
            tarefas_concluidas = df_loja_check[df_loja_check["Status"] == "Concluído"]["Tarefa"].tolist()
            
            pendentes = [t for t in tarefas_checklist if t not in tarefas_concluidas]
            
            with cols_check[i]:
                st.markdown(f"**{nome_loja}**")
                if pendentes:
                    for p in pendentes:
                        st.markdown(f"❌ {p}")
                else:
                    if tarefas_checklist:
                        st.success("Tudo concluído! 🎉")
                    else:
                        st.info("Nenhuma tarefa configurada.")
        
        st.divider()
        st.subheader(f"📋 Registros Recentes ({'Todas' if loja_selecionada_admin == 'Todas as Lojas' else loja_selecionada_admin})")
        # Mostrar apenas os dados que já passaram pelo filtro de loja e data
        st.dataframe(
            df_filtrado.tail(15).sort_values(by="Data_Hora", ascending=False).drop(columns=['Data', 'Data_Date'], errors='ignore'), 
            use_container_width=True
        )
        
    else:
        st.info("Nenhum dado registrado ainda ou sem conexão.")
