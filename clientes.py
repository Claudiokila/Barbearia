# NÃO ADICIONE NADA ANTES DESTA LINHA - NEM IMPORTS, NEM COMENTÁRIOS!
import streamlit as st
st.set_page_config(
    page_title="Agendamento de Corte",
    page_icon="✂️",
    layout="centered"
)

# SÓ AQUI IMPORTE OUTRAS BIBLIOTECAS
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2 import service_account
import urllib.parse
import base64

# O RESTO DO SEU CÓDIGO CONTINUA AQUI...
# [todo o restante do seu código original]

    # CONSTANTES
    SPREADSHEET_ID = "1z0vz0WecZAgZp7PkV3zsx3HHXBv6W_fUEtuDrniY5Jk"
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Função para conectar ao Google Sheets com cache
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

    # Função para carregar configurações com cache
    @st.cache_data(ttl=300)
    def carregar_configuracoes(_spreadsheet):
        try:
            worksheet = _spreadsheet.worksheet("Configuracoes")
            records = worksheet.get_all_records()
            
            horarios = [str(r['Horarios']) for r in records if 'Horarios' in r and r['Horarios']]
            servicos = []
            precos = []
            
            for r in records:
                if 'Servicos' in r and 'Precos' in r and r['Servicos'] and r['Precos']:
                    servicos.append(r['Servicos'])
                    try:
                        precos.append(float(r['Precos']))
                    except ValueError:
                        continue
            
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
    def salvar_agendamento(_spreadsheet, dados):
        try:
            worksheet = _spreadsheet.worksheet("Agendamentos")
            worksheet.append_row(dados)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar agendamento: {str(e)}")
            return False

    # Função para remover horário agendado
    def remover_horario_disponivel(_spreadsheet, hora_agendada):
        try:
            worksheet = _spreadsheet.worksheet("Configuracoes")
            records = worksheet.get_all_records()
            
            rows_to_delete = []
            for i, r in enumerate(records, start=2):
                if 'Horarios' in r and str(r['Horarios']) == hora_agendada:
                    rows_to_delete.append(i)
            
            for row_num in sorted(rows_to_delete, reverse=True):
                worksheet.delete_rows(row_num)
            
            st.cache_data.clear()
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

    st.title("✂️ Agendamento de Corte")

    # Conectar ao Google Sheets
    spreadsheet = get_spreadsheet()

    # Carregar configurações
    config = carregar_configuracoes(spreadsheet)

    if not config:
        st.error("Erro ao carregar configurações. Por favor, tente novamente mais tarde.")
        st.stop()

    # Formulário de agendamento
    with st.form("agendamento_form"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo*")
        with col2:
            telefone = st.text_input("Telefone para contato* (com DDD)")    
        
        col3, col4, col5 = st.columns(3)
        with col3:
            servico_info = st.selectbox(
                "Serviço desejado:", 
                options=config['servicos'], 
                format_func=lambda x: f"{x[0]} - R${x[1]:.2f}"
            )
            servico = servico_info[0]
            preco = servico_info[1]
        with col4:
            data_str = st.selectbox("Data disponível:", options=config['datas'], disabled=True)
            data = datetime.strptime(data_str, "%d/%m/%Y").date()
        with col5:    
            hora_str = st.selectbox("Horário disponível:", options=config['horarios'])
            hora = datetime.strptime(hora_str, "%H:%M").time()
        
        observacoes = st.text_area("Observações ou detalhes do corte")
        
        if st.form_submit_button("Agendar Horário"):
            if nome and telefone:
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
                    if remover_horario_disponivel(spreadsheet, hora_str):
                        st.success("Horário removido da lista de disponíveis com sucesso!")
                    
                    mensagem = f"Olá, gostaria de confirmar meu agendamento:\n\n"
                    mensagem += f"*Nome:* {nome}\n"
                    mensagem += f"*Serviço:* {servico} (R${preco:.2f})\n"
                    mensagem += f"*Data:* {data.strftime('%d/%m/%Y')}\n"
                    mensagem += f"*Horário:* {hora.strftime('%H:%M')}\n"
                    if observacoes:
                        mensagem += f"*Observações:* {observacoes}\n"
                    
                    telefone_limpo = ''.join(filter(str.isdigit, telefone))
                    whatsapp_url = f"https://wa.me/55{telefone_limpo}?text={urllib.parse.quote(mensagem)}"
                    
                    st.success("Agendamento realizado com sucesso! Clique abaixo para confirmar pelo WhatsApp:")
                    
                    st.markdown(
                        f'<a href="{whatsapp_url}" class="whatsapp-btn" target="_blank">'
                        'Confirmar agendamento pelo WhatsApp'
                        '</a>',
                        unsafe_allow_html=True
                    )
            else:
                st.error("Por favor, preencha pelo menos o nome e telefone.")

    st.markdown("</div>", unsafe_allow_html=True)

    # Rodapé
    st.markdown("---")
    st.caption(f"© {datetime.now().year} Barbearia Style - Todos os direitos reservados")

if __name__ == "__main__":
    main()