import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import numpy as np

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# Lê as credenciais do secrets
creds_dict = st.secrets["gcp_service_account"]

# Escopos de acesso
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# ID da planilha
SPREADSHEET_ID = "1z0vz0WecZAgZp7PkV3zsx3HHXBv6W_fUEtuDrniY5Jk"

# Função para conectar ao Google Sheets
def conectar_google_sheets():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)

# Configurações do sistema
MAX_AGENDAMENTOS_POR_HORARIO = 1  # Quantidade máxima de clientes no mesmo horário



# Função para carregar dados
def carregar_dados(spreadsheet, sheet_name):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Tratamento especial para cada aba
        if sheet_name == "Configuracoes":
            if 'Precos' in df.columns:
                df['Precos'] = pd.to_numeric(df['Precos'], errors='coerce')
        
        elif sheet_name == "Agendamentos":
            if 'Preco' in df.columns:
                df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
            if 'Data_Registro' in df.columns:
                df['Data_Registro'] = pd.to_datetime(df['Data_Registro'], dayfirst=True, errors='coerce')
        
        return df.replace('', np.nan).dropna(how='all')
    
    except Exception as e:
        st.error(f"Erro ao carregar {sheet_name}: {str(e)}")
        return pd.DataFrame()

# Função para salvar dados
def salvar_dados(spreadsheet, sheet_name, df):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        worksheet.clear()
        
        # Converter NaN para None e garantir strings
        dados = df.fillna('').astype(str).values.tolist()
        worksheet.update([df.columns.tolist()] + dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar em {sheet_name}: {str(e)}")
        return False

# Função para verificar horários disponíveis
def verificar_horarios_disponiveis(spreadsheet, data_selecionada):
    try:
        # Carregar dados
        df_config = carregar_dados(spreadsheet, "Configuracoes")
        df_agendamentos = carregar_dados(spreadsheet, "Agendamentos")
        
        # Obter todos horários configurados
        todos_horarios = df_config['Horarios'].dropna().unique().tolist()
        
        # Filtrar agendamentos para a data selecionada
        agendamentos_data = df_agendamentos[df_agendamentos['Data'] == data_selecionada]
        
        # Contar quantos agendamentos por horário
        contagem_horarios = agendamentos_data['Hora'].value_counts().to_dict()
        
        # Determinar horários disponíveis
        horarios_disponiveis = []
        for horario in todos_horarios:
            if horario not in contagem_horarios or contagem_horarios[horario] < MAX_AGENDAMENTOS_POR_HORARIO:
                horarios_disponiveis.append(horario)
        
        return horarios_disponiveis
    
    except Exception as e:
        st.error(f"Erro ao verificar horários: {str(e)}")
        return []

# Configuração da página
st.set_page_config(
    page_title="Retaguarda - Barbearia",
    page_icon="✂️",
    layout="wide"
)

# Título principal
st.title("✂️ Painel de Retaguarda - Barbearia")

# Conectar ao Google Sheets
spreadsheet = conectar_google_sheets()

# Carregar dados iniciais
df_config = carregar_dados(spreadsheet, "Configuracoes")
df_agendamentos = carregar_dados(spreadsheet, "Agendamentos")

# Dados padrão se a planilha estiver vazia
if df_config.empty:
    dados_padrao = {
        'Horarios': ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00'],
        'Servicos': ['Corte', 'Barba', 'Corte + Barba', 'Sobrancelha', 'Pezinho'],
        'Precos': [30.00, 20.00, 45.00, 10.00, 5.00],
        'Datas': [
            datetime.now().strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y'),
            (datetime.now() + timedelta(days=2)).strftime('%d/%m/%Y')
        ]
    }
    df_config = pd.DataFrame(dados_padrao)
    salvar_dados(spreadsheet, "Configuracoes", df_config)

# Abas do painel
tab1, tab2, tab3 = st.tabs(["Configurações", "Agendamentos", "Relatórios"])

with tab1:
    st.header("Configurações da Barbearia")
    
    with st.form("config_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Horários Disponíveis")
            horarios = st.text_area(
                "Horários (um por linha)", 
                value="\n".join(df_config['Horarios'].dropna().astype(str).tolist()),
                height=200
            )
        
        with col2:
            st.subheader("Serviços e Preços")
            servicos_precos = st.text_area(
                "Serviço:Preço (um por linha)", 
                value="\n".join([
                    f"{s}:{p}" for s, p in zip(
                        df_config['Servicos'].dropna().astype(str).tolist(), 
                        df_config['Precos'].dropna().astype(float).tolist()
                    )
                ]),
                height=200
            )
        
        with col3:
            st.subheader("Datas Disponíveis")
            datas = st.text_area(
                "Datas (DD/MM/YYYY)", 
                value="\n".join(df_config['Datas'].dropna().astype(str).tolist()),
                height=200
            )
        
        if st.form_submit_button("Salvar Configurações"):
            try:
                # Processar dados
                horarios_lista = [h.strip() for h in horarios.split('\n') if h.strip()]
                
                servicos = []
                precos = []
                for linha in servicos_precos.split('\n'):
                    if ':' in linha:
                        s, p = linha.split(':', 1)
                        servicos.append(s.strip())
                        try:
                            precos.append(float(p.strip()))
                        except ValueError:
                            st.warning(f"Ignorando preço inválido: {p}")
                
                datas_lista = [d.strip() for d in datas.split('\n') if d.strip()]
                
                # Criar DataFrame
                df_novo = pd.DataFrame({
                    'Horarios': pd.Series(horarios_lista),
                    'Servicos': pd.Series(servicos),
                    'Precos': pd.Series(precos),
                    'Datas': pd.Series(datas_lista)
                })
                
                if salvar_dados(spreadsheet, "Configuracoes", df_novo):
                    st.success("Configurações salvas com sucesso!")
                    st.rerun()
            
            except Exception as e:
                st.error(f"Erro ao processar dados: {str(e)}")

with tab2:
    st.header("Agendamentos")
    
    # Seção para novo agendamento
    with st.form("novo_agendamento_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            data_selecionada = st.selectbox(
                "Data*",
                options=df_config['Datas'].dropna().astype(str).tolist()
            )
            
            # Obter horários disponíveis para a data selecionada
            horarios_disponiveis = verificar_horarios_disponiveis(spreadsheet, data_selecionada)
            
            if not horarios_disponiveis:
                st.warning("Não há horários disponíveis para esta data!")
            else:
                hora_selecionada = st.selectbox(
                    "Horário*",
                    options=horarios_disponiveis
                )
            
            servico_selecionado = st.selectbox(
                "Serviço*",
                options=df_config['Servicos'].dropna().astype(str).tolist()
            )
        
        with col2:
            nome_cliente = st.text_input("Nome do Cliente*", max_chars=50)
            telefone_cliente = st.text_input("Telefone*", max_chars=15)
            observacoes = st.text_area("Observações", max_chars=200)
        
        if st.form_submit_button("Agendar"):
            if nome_cliente and telefone_cliente and horarios_disponiveis:
                try:
                    # Verificar novamente a disponibilidade (para evitar conflitos)
                    horarios_atuais = verificar_horarios_disponiveis(spreadsheet, data_selecionada)
                    
                    if hora_selecionada not in horarios_atuais:
                        st.error("Este horário já foi reservado. Por favor, escolha outro.")
                    else:
                        # Obter preço do serviço
                        idx = df_config['Servicos'].astype(str) == servico_selecionado
                        preco = df_config.loc[idx, 'Precos'].values[0]
                        
                        # Adicionar agendamento
                        worksheet = spreadsheet.worksheet("Agendamentos")
                        novo_agendamento = [
                            data_selecionada,
                            hora_selecionada,
                            nome_cliente,
                            telefone_cliente,
                            servico_selecionado,
                            float(preco),
                            observacoes,
                            datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                        ]
                        worksheet.append_row(novo_agendamento)
                        
                        st.success("Agendamento realizado com sucesso!")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao agendar: {str(e)}")
            else:
                st.error("Preencha todos os campos obrigatórios!")
    
    # Visualização de agendamentos
    st.subheader("Agendamentos Existentes")
    df_agendamentos = carregar_dados(spreadsheet, "Agendamentos")
    
    if not df_agendamentos.empty:
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            filtro_data = st.selectbox(
                "Filtrar por data",
                options=['Todas'] + sorted(df_agendamentos['Data'].astype(str).unique().tolist())
            )
        
        with col2:
            filtro_servico = st.selectbox(
                "Filtrar por serviço",
                options=['Todos'] + sorted(df_agendamentos['Serviço'].astype(str).unique().tolist())
            )
        
        # Aplicar filtros
        if filtro_data != 'Todas':
            df_filtrado = df_agendamentos[df_agendamentos['Data'].astype(str) == filtro_data]
        else:
            df_filtrado = df_agendamentos.copy()
            
        if filtro_servico != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Serviço'].astype(str) == filtro_servico]
        
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Remoção de agendamento
        st.subheader("Remover Agendamento")
        opcoes = [
            f"{row['Data']} {row['Hora']} - {row['Nome']} ({row['Serviço']})"
            for _, row in df_filtrado.iterrows()
        ]
        
        if opcoes:
            indice = st.selectbox(
                "Selecione o agendamento para remover",
                options=range(len(opcoes)),
                format_func=lambda x: opcoes[x]
            )
            
            if st.button("Remover Agendamento"):
                try:
                    # Obter o índice real na planilha
                    id_para_remover = df_filtrado.iloc[indice].name + 2  # +2 para cabeçalho e indexação 1-based
                    
                    # Remover agendamento
                    spreadsheet.worksheet("Agendamentos").delete_rows(id_para_remover)
                    
                    st.success("Agendamento removido com sucesso!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao remover: {str(e)}")
    else:
        st.info("Nenhum agendamento cadastrado.")

with tab3:
    st.header("Relatórios")
    
    df_agendamentos = carregar_dados(spreadsheet, "Agendamentos")
    
    if not df_agendamentos.empty:
        # Métricas
        st.subheader("Métricas")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Agendamentos", len(df_agendamentos))
        
        with col2:
            faturamento = df_agendamentos['Preco'].sum()
            st.metric("Faturamento Total", f"R$ {faturamento:.2f}")
        
        with col3:
            ticket_medio = df_agendamentos['Preco'].mean()
            st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
        
        # Gráficos
        st.subheader("Análise por Serviço")
        st.bar_chart(df_agendamentos['Serviço'].value_counts())
        
        st.subheader("Faturamento por Data")
        try:
            df_agendamentos['Data'] = pd.to_datetime(df_agendamentos['Data'], dayfirst=True)
            st.line_chart(df_agendamentos.groupby('Data')['Preco'].sum())
        except:
            st.warning("Não foi possível gerar gráfico de faturamento")
        
        # Exportar
        st.subheader("Exportar Dados")
        csv = df_agendamentos.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar como CSV",
            data=csv,
            file_name=f"agendamentos_barbearia_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )
    else:
        st.info("Nenhum dado disponível para relatórios.")

st.markdown("---")
st.caption("© 2023 Barbearia Style - Painel Administrativo")