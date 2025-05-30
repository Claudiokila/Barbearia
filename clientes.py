import streamlit as st
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2 import service_account
import urllib.parse
import base64

import streamlit as st

hide_streamlit_style = """
    <style>
    #MainMenu, header, footer {visibility: hidden; height: 0px;}

    /* Forçar ocultação do badge do Streamlit Cloud */
    .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    
    [data-testid="stDeployButton"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Forçar ocultar o container inteiro que carrega esse botão */
    a[href^="https://streamlit.io/cloud"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Se existir um div container específico */
    div[class*="viewerBadge"] {
        display: none !important;
        visibility: hidden !important;
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
WHATSAPP_NUMBER = "558599339802"  # Número fixo para onde os agendamentos devem ser enviados

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

# Função para carregar configurações
def carregar_configuracoes(spreadsheet):
    try:
        worksheet = spreadsheet.worksheet("Configuracoes")
        records = worksheet.get_all_records()
        
        horarios = [str(r['Horarios']) for r in records if 'Horarios' in r and r['Horarios']]
        servicos = []
        precos = []
        
        for r in records:
            if 'Servicos' in r and 'Precos' in r and r['Servicos'] and r['Precos']:
                servicos.append(r['Servicos'])
                precos.append(float(r['Precos']))
        
        datas = [str(r['Datas']) for r in records if 'Datas' in r and r['Datas']]
        
        return {
            'horarios': horarios,
            'servicos': list(zip(servicos, precos)),
            'datas': datas
        }
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {str(e)}")
        return None

# Função para salvar agendamento
def salvar_agendamento(spreadsheet, dados):
    try:
        worksheet = spreadsheet.worksheet("Agendamentos")
        worksheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar agendamento: {str(e)}")
        return False

# Função para remover horário agendado da lista de disponíveis
def remover_horario_disponivel(spreadsheet, hora_agendada):
    try:
        worksheet = spreadsheet.worksheet("Configuracoes")
        records = worksheet.get_all_records()
        
        # Encontrar todas as linhas que contêm o horário agendado
        rows_to_delete = []
        for i, r in enumerate(records, start=2):  # start=2 porque a planilha começa na linha 2 (linha 1 é cabeçalho)
            if 'Horarios' in r and str(r['Horarios']) == hora_agendada:
                rows_to_delete.append(i)
        
        # Remover as linhas encontradas (de trás para frente para não afetar os índices)
        for row_num in sorted(rows_to_delete, reverse=True):
            worksheet.delete_rows(row_num)
            
        return True
    except Exception as e:
        st.error(f"Erro ao remover horário disponível: {str(e)}")
        return False

# Função para adicionar background
def set_bg_hack():
    try:
        with open('BACK.jpg', "rb") as f:
            img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode()
        
        st.markdown(
            f"""
            <style>
            .stApp {{
                background: url("data:image/jpg;base64,{img_base64}");
                background-size: cover;
                background-repeat: no-repeat;
                background-position: center center;
                background-attachment: fixed;
            }}
            .main {{
                background-color: rgba(0, 0, 0, 0.7);
                padding: 2rem;
                border-radius: 15px;
                margin: 2rem auto;
                width: 85%;
                max-width: 700px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                border: 2px solid #FFD700;
                color: white !important;
            }}
            h1, h2, h3, h4, h5, h6, label, p, .stMarkdown {{
                color: white !important;
            }}
            .stFormSubmitButton>button {{
                background-color: #FFD700 !important;
                color: #000000 !important;
                font-weight: bold;
                border: 1px solid #000000 !important;
            }}
            .stFormSubmitButton>button:hover {{
                background-color: #FFC800 !important;
                color: #000000 !important;
            }}
            .whatsapp-btn {{
                background-color: #25D366;
                color: white !important;
                padding: 0.7rem  1.5rem;
                border-radius: 8px;
                text-decoration: none;
                display: inline-block;
                margin-top: 1.5rem;
                font-weight: bold;
                font-size: 1.1rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }}
            .stTextInput>div>div>input, 
            .stTextArea>div>div>textarea,
            .stDateInput>div>div>input,
            .stTimeInput>div>div>input {{
                background-color: rgba(255, 255, 255, 0.9) !important;
                color: #333333 !important;
            }}
            .stDateInput>div>div>input {{
                pointer-events: none;
                background-color: #e9e9e9 !important;
            }}
            .error-message {{
                color: #FF6347 !important;
                font-weight: bold;
            }}
            .no-availability {{
                color: #FFD700 !important;
                font-size: 1.2rem;
                text-align: center;
                margin: 2rem 0;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.markdown(
            """
            <style>
            .main {
                background-color: rgba(0, 0, 0, 0.7);
                padding: 2rem;
                border-radius: 15px;
                margin: 2rem auto;
                width: 85%;
                max-width: 700px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                border: 2px solid #FFD700;
                color: white !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

# Aplicar estilo
set_bg_hack()

# Conteúdo principal
st.markdown("<div class='main'>", unsafe_allow_html=True)

st.title("✂️BARBEARIA MUCACÓ✂️")

# Conectar ao Google Sheets
spreadsheet = get_spreadsheet()

# Carregar configurações
config = carregar_configuracoes(spreadsheet)

if not config:
    st.error("Erro ao carregar configurações. Por favor, tente novamente mais tarde.")
    st.stop()

# Verificar disponibilidade
if not config['datas'] or not config['horarios']:
    st.markdown('<p class="no-availability">⚠️ No momento não há horários disponíveis para agendamento. Por favor, volte mais tarde.</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Formulário de agendamento
with st.form("agendamento_form"):
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome completo*", key="nome")
    with col2:
        telefone = st.text_input("Telefone para contato* (com DDD)", key="telefone")    
    
    col3, col4, col5 = st.columns(3)
    with col3:
        # Seleção de serviço com preços
        servico_info = st.selectbox("Serviço desejado:", options=config['servicos'], format_func=lambda x: f"{x[0]} - R${x[1]:.2f}", key="servico")
        servico = servico_info[0]
        preco = servico_info[1]
    with col4:
        # Seleção de data
        data_str = st.selectbox("Data disponível:", options=config['datas'], key="data")
        data = datetime.strptime(data_str, "%d/%m/%Y").date()

    with col5:    
        # Seleção de horário
        hora_str = st.selectbox("Horário disponível:", options=config['horarios'], key="hora")
        hora = datetime.strptime(hora_str, "%H:%M").time()
    
    observacoes = st.text_area("Observações ou detalhes do corte", key="observacoes")
    
    submitted = st.form_submit_button("Agendar Horário")
    
    if submitted:
        if nome and telefone:
            # Preparar dados para salvar
            dados_agendamento = [
                data.strftime('%d/%m/%Y'),
                hora.strftime('%H:%M'),
                nome,
                telefone,
                servico,
                preco,
                observacoes,
                datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            ]
            
            if salvar_agendamento(spreadsheet, dados_agendamento):
                # Remover o horário agendado da lista de disponíveis
                if remover_horario_disponivel(spreadsheet, hora_str):
                    st.success("Horário agendado com sucesso!")
                
                # Mensagem para WhatsApp
                mensagem = f"Olá, gostaria de confirmar meu agendamento:\n\n"
                mensagem += f"*Nome:* {nome}\n"
                mensagem += f"*Telefone:* {telefone}\n"
                mensagem += f"*Serviço:* {servico} (R${preco:.2f})\n"
                mensagem += f"*Data:* {data.strftime('%d/%m/%Y')}\n"
                mensagem += f"*Horário:* {hora.strftime('%H:%M')}\n"
                if observacoes:
                    mensagem += f"*Observações:* {observacoes}\n"
                
                whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(mensagem)}"
                
                st.markdown(
                    f'<a href="{whatsapp_url}" class="whatsapp-btn" target="_blank">'
                    'Confirmar agendamento pelo WhatsApp'
                    '</a>',
                    unsafe_allow_html=True
                )
            else:
                st.error("Ocorreu um erro ao salvar o agendamento. Por favor, tente novamente.")
        else:
            st.error("Por favor, preencha pelo menos o nome e telefone.")

st.markdown("</div>", unsafe_allow_html=True)

# Rodapé
st.markdown("---")
st.caption("© 2023 CB MAIS - Todos os direitos reservados")