import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, timedelta
import numpy as np
from google.oauth2 import service_account
import time

# Configuração da página DEVE ser a primeira coisa
st.set_page_config(
    page_title="Retaguarda - Barbearia",
    page_icon="✂️",
    layout="wide"
)

# Estilos CSS
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo para os cards de agendamento */
    .agendamento-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .agendamento-card h4 {
        margin-top: 0;
        color: #333;
    }
    .agendamento-card p {
        margin-bottom: 5px;
    }
    .horario-tag {
        background-color: #4CAF50;
        color: white;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.9em;
        display: inline-block;
        margin-right: 5px;
    }
    .servico-tag {
        background-color: #2196F3;
        color: white;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.9em;
        display: inline-block;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# CONSTANTES
MAX_AGENDAMENTOS_POR_HORARIO = 1
SPREADSHEET_ID = "1z0vz0WecZAgZp7PkV3zsx3HHXBv6W_fUEtuDrniY5Jk"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Função para conectar ao Google Sheets
@st.cache_resource(ttl=3600)
def get_gspread_client():
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {str(e)}")
        st.stop()

# Função para obter a planilha
def get_spreadsheet():
    client = get_gspread_client()
    return client.open_by_key(SPREADSHEET_ID)

# Função para parsear datas
def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except:
        return None

# Função para carregar dados com verificação robusta
@st.cache_data(ttl=300)
def carregar_dados(_spreadsheet, sheet_name):
    try:
        worksheet = _spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Debug: Mostrar dados brutos
        st.session_state[f'debug_{sheet_name}'] = df.copy()
        
        # Tratamento especial para cada aba
        if sheet_name == "Configuracoes":
            if 'Precos' in df.columns:
                df['Precos'] = pd.to_numeric(df['Precos'], errors='coerce')
        
        elif sheet_name == "Agendamentos":
            if 'Preco' in df.columns:
                df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
            if 'Data' in df.columns:
                df['Data'] = df['Data'].apply(parse_date)
            if 'Data_Registro' in df.columns:
                df['Data_Registro'] = pd.to_datetime(df['Data_Registro'], dayfirst=True, errors='coerce')
        
        return df.replace('', np.nan).dropna(how='all')
    
    except Exception as e:
        st.error(f"Erro ao carregar {sheet_name}: {str(e)}")
        return pd.DataFrame()

# Função para salvar dados
def salvar_dados(_spreadsheet, sheet_name, df):
    try:
        if df.empty:
            st.warning("Nenhum dado para salvar!")
            return False
            
        worksheet = _spreadsheet.worksheet(sheet_name)
        worksheet.clear()
        
        # Converter datas para string antes de salvar
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%d/%m/%Y')
        
        dados = df.fillna('').astype(str).values.tolist()
        worksheet.update([df.columns.tolist()] + dados)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar em {sheet_name}: {str(e)}")
        return False

# Função para verificar horários disponíveis
@st.cache_data(ttl=60)
def verificar_horarios_disponiveis(_spreadsheet, data_selecionada):
    try:
        df_config = carregar_dados(_spreadsheet, "Configuracoes")
        df_agendamentos = carregar_dados(_spreadsheet, "Agendamentos")
        
        if df_config.empty or df_agendamentos.empty:
            return df_config['Horarios'].dropna().unique().tolist()
        
        todos_horarios = df_config['Horarios'].dropna().unique().tolist()
        
        # Converter para string para comparação
        data_str = parse_date(data_selecionada)
        if data_str:
            data_str = data_str.strftime('%d/%m/%Y')
        
        agendamentos_data = df_agendamentos[df_agendamentos['Data'].astype(str) == data_str]
        contagem_horarios = agendamentos_data['Hora'].value_counts().to_dict()
        
        return [
            horario for horario in todos_horarios
            if horario not in contagem_horarios or 
            contagem_horarios[horario] < MAX_AGENDAMENTOS_POR_HORARIO
        ]
    
    except Exception as e:
        st.error(f"Erro ao verificar horários: {str(e)}")
        return []

# Função para verificar consistência
def verificar_consistencia():
    spreadsheet = get_spreadsheet()
    df_agendamentos = carregar_dados(spreadsheet, "Agendamentos")
    
    st.subheader("Verificação de Consistência")
    
    # Verificar dados faltantes
    st.write("### Dados Faltantes")
    missing_data = df_agendamentos.isnull().sum()
    st.write(missing_data)
    
    # Verificar datas inválidas
    st.write("### Datas Inválidas")
    invalid_dates = df_agendamentos[df_agendamentos['Data'].isna()]
    st.write(invalid_dates)
    
    # Verificar duplicatas
    st.write("### Agendamentos Duplicados")
    duplicates = df_agendamentos[df_agendamentos.duplicated(subset=['Data', 'Hora', 'Nome'], keep=False)]
    st.write(duplicates)

# Interface principal
def main():
    st.title("✂️ Painel de Retaguarda - Barbearia")
    
    # Botão de atualização manual
    if st.button("Atualizar Dados (Forçar Recarregamento)"):
        st.cache_data.clear()
        st.rerun()
    
    spreadsheet = get_spreadsheet()
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["Configurações", "Agendamentos", "Relatórios", "Depuração"])
    
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
                    max_len = max(len(horarios_lista), len(servicos), len(datas_lista))
                    df_novo = pd.DataFrame({
                        'Horarios': pd.Series(horarios_lista + [None]*(max_len - len(horarios_lista))),
                        'Servicos': pd.Series(servicos + [None]*(max_len - len(servicos))),
                        'Precos': pd.Series(precos + [None]*(max_len - len(precos))),
                        'Datas': pd.Series(datas_lista + [None]*(max_len - len(datas_lista)))
                    })
                    
                    if salvar_dados(spreadsheet, "Configuracoes", df_novo):
                        st.success("Configurações salvas com sucesso!")
                        time.sleep(2)
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
                        # Verificação de disponibilidade em tempo real
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
                            st.cache_data.clear()
                            
                            st.success("Agendamento realizado com sucesso!")
                            time.sleep(2)
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"Erro ao agendar: {str(e)}")
                else:
                    st.error("Preencha todos os campos obrigatórios!")
        
        # Visualização de agendamentos
        st.subheader("Agendamentos Existentes")
        
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
                    options=['Todos'] + sorted(df_agendamentos['Serviço'].astype(str).unique().tolist()))
                
            # Aplicar filtros
            df_filtrado = df_agendamentos.copy()
            if filtro_data != 'Todas':
                df_filtrado = df_filtrado[df_filtrado['Data'].astype(str) == filtro_data]
            if filtro_servico != 'Todos':
                df_filtrado = df_filtrado[df_filtrado['Serviço'].astype(str) == filtro_servico]
            
            # Exibir agendamentos como cards estilizados
            if not df_filtrado.empty:
                st.write(f"**Total de agendamentos:** {len(df_filtrado)}")
                
                for _, row in df_filtrado.sort_values(['Data', 'Hora']).iterrows():
                    with st.container():
                        st.markdown(
                            f"""
                            <div class="agendamento-card">
                                <h4>{row['Nome']}</h4>
                                <p><span class="horario-tag">{row['Hora']}</span> <span class="servico-tag">{row['Serviço']}</span></p>
                                <p><strong>Data:</strong> {row['Data']}</p>
                                <p><strong>Telefone:</strong> {row['Telefone']}</p>
                                <p><strong>Preço:</strong> R$ {row['Preco']:.2f}</p>
                                <p><strong>Observações:</strong> {row.get('Observacoes', 'Nenhuma')}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.info("Nenhum agendamento encontrado com os filtros selecionados.")
            
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
                        id_para_remover = df_filtrado.iloc[indice].name + 2  # +2 porque a planilha tem cabeçalho e índice começa em 1
                        spreadsheet.worksheet("Agendamentos").delete_rows(id_para_remover)
                        st.cache_data.clear()
                        
                        st.success("Agendamento removido com sucesso!")
                        time.sleep(2)
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
    
    with tab4:
        st.header("Depuração e Verificação")
        
        st.subheader("Dados Brutos - Configurações")
        if 'debug_Configuracoes' in st.session_state:
            st.write(st.session_state['debug_Configuracoes'])
        else:
            st.warning("Dados de configuração não carregados")
        
        st.subheader("Dados Brutos - Agendamentos")
        if 'debug_Agendamentos' in st.session_state:
            st.write(st.session_state['debug_Agendamentos'])
        else:
            st.warning("Dados de agendamentos não carregados")
        
        verificar_consistencia()
    
    st.markdown("---")
    st.caption(f"© {datetime.now().year} Barbearia Style - Painel Administrativo")

if __name__ == "__main__":
    main()