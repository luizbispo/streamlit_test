import datetime
import textwrap
import streamlit as st

st.title("🏦 Sistema Bancário")

class Usuario:
    def __init__(self, nome, data_nascimento, cpf, endereco):
        self.nome = nome
        self.data_nascimento = data_nascimento
        self.cpf = cpf
        self.endereco = endereco

class Conta:
    def __init__(self, agencia, numero_conta, usuario, limite_saques=3, limite_valor_saque=500.0):
        self.agencia = agencia
        self.numero_conta = numero_conta
        self.usuario = usuario
        self.saldo = 0.0
        self.extrato = []
        self.numero_saques = 0
        self.limite_saques = limite_saques
        self.limite_valor_saque = limite_valor_saque
    
    def depositar(self, valor):
        if valor > 0:
            self.saldo += valor
            self.extrato.append(f"[{self._data_atual()}] Depósito:\tR$ {valor:.2f}")
            return True, "Depósito realizado com sucesso!"
        return False, "Operação falhou! O valor informado é inválido."
    
    def sacar(self, valor):
        excedeu_saldo = valor > self.saldo
        excedeu_limite = valor > self.limite_valor_saque
        excedeu_saques = self.numero_saques >= self.limite_saques

        if excedeu_saldo:
            return False, "Operação falhou! Saldo insuficiente."
        elif excedeu_limite:
            return False, "Operação falhou! Valor excede o limite."
        elif excedeu_saques:
            return False, "Operação falhou! Limite de saques diários excedido."
        elif valor > 0:
            self.saldo -= valor
            self.extrato.append(f"[{self._data_atual()}] Saque:\t\tR$ {valor:.2f}")
            self.numero_saques += 1
            return True, "Saque realizado com sucesso!"
        else:
            return False, "Operação falhou! Valor inválido."
    
    def exibir_extrato(self):
        extrato_texto = "================ EXTRATO ================\n"
        if self.extrato:
            for linha in self.extrato:
                extrato_texto += linha + "\n"
        else:
            extrato_texto += "Nenhuma movimentação realizada.\n"
        extrato_texto += f"\nSaldo:\t\tR$ {self.saldo:.2f}\n"
        extrato_texto += "=========================================="
        return extrato_texto
    
    def _data_atual(self):
        return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class Banco:
    def __init__(self, agencia):
        self.agencia = agencia
        self.usuarios = []
        self.contas = []
    
    def criar_usuario(self, nome, data_nascimento, cpf, endereco):
        if self.filtrar_usuario(cpf):
            return False, "Já existe um usuário com esse CPF!"
        
        novo_usuario = Usuario(nome, data_nascimento, cpf, endereco)
        self.usuarios.append(novo_usuario)
        return True, "Usuário criado com sucesso!"
    
    def filtrar_usuario(self, cpf):
        for usuario in self.usuarios:
            if usuario.cpf == cpf:
                return usuario
        return None
    
    def criar_conta(self, cpf_usuario):
        usuario = self.filtrar_usuario(cpf_usuario)
        if not usuario:
            return False, "Usuário não encontrado! Criação de conta cancelada."
        
        numero_conta = len(self.contas) + 1
        nova_conta = Conta(self.agencia, numero_conta, usuario)
        self.contas.append(nova_conta)
        return True, "Conta criada com sucesso!", nova_conta
    
    def listar_contas(self):
        if not self.contas:
            return "Nenhuma conta cadastrada."
        
        lista_texto = "========= LISTA DE CONTAS =========\n"
        for conta in self.contas:
            linha = f"""
                Agência: {conta.agencia}
                Conta: {conta.numero_conta}
                Titular: {conta.usuario.nome}
                CPF: {conta.usuario.cpf}
            """
            lista_texto += "=" * 40 + "\n"
            lista_texto += textwrap.dedent(linha) + "\n"
        return lista_texto

# Inicializar o banco na sessão do Streamlit
if 'banco' not in st.session_state:
    st.session_state.banco = Banco("0001")
    st.session_state.conta_atual = None

banco = st.session_state.banco
conta_atual = st.session_state.conta_atual

# Menu principal
st.sidebar.title("Menu Principal")
opcao = st.sidebar.radio("Selecione uma opção:", 
                         ["Depositar", "Sacar", "Extrato", "Usuários/Contas"])

# Operações bancárias
if opcao == "Depositar":
    st.header("💰 Depositar")
    
    if not conta_atual:
        st.warning("Selecione uma conta primeiro na seção Usuários/Contas!")
    else:
        valor = st.number_input("Valor para depósito:", min_value=0.01, step=0.01)
        if st.button("Realizar Depósito"):
            sucesso, mensagem = conta_atual.depositar(valor)
            if sucesso:
                st.success(mensagem)
            else:
                st.error(mensagem)

elif opcao == "Sacar":
    st.header("💸 Sacar")
    
    if not conta_atual:
        st.warning("Selecione uma conta primeiro na seção Usuários/Contas!")
    else:
        valor = st.number_input("Valor para saque:", min_value=0.01, step=0.01)
        if st.button("Realizar Saque"):
            sucesso, mensagem = conta_atual.sacar(valor)
            if sucesso:
                st.success(mensagem)
            else:
                st.error(mensagem)

elif opcao == "Extrato":
    st.header("📊 Extrato")
    
    if not conta_atual:
        st.warning("Selecione uma conta primeiro na seção Usuários/Contas!")
    else:
        extrato = conta_atual.exibir_extrato()
        st.text_area("Extrato da Conta:", extrato, height=300)

elif opcao == "Usuários/Contas":
    st.header("👥 Usuários e Contas")
    
    sub_opcao = st.radio("Selecione:", 
                         ["Novo Usuário", "Nova Conta", "Listar Contas", "Selecionar Conta"])
    
    if sub_opcao == "Novo Usuário":
        st.subheader("Cadastrar Novo Usuário")
        
        with st.form("novo_usuario"):
            nome = st.text_input("Nome completo:")
            data_nascimento = st.text_input("Data de nascimento (dd-mm-aaaa):")
            cpf = st.text_input("CPF (somente números):")
            endereco = st.text_input("Endereço (logradouro, nro - bairro - cidade/UF):")
            
            if st.form_submit_button("Criar Usuário"):
                if nome and data_nascimento and cpf and endereco:
                    sucesso, mensagem = banco.criar_usuario(nome, data_nascimento, cpf, endereco)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)
                else:
                    st.error("Preencha todos os campos!")
    
    elif sub_opcao == "Nova Conta":
        st.subheader("Criar Nova Conta")
        
        cpf = st.text_input("CPF do usuário:")
        if st.button("Criar Conta"):
            if cpf:
                sucesso, mensagem, nova_conta = banco.criar_conta(cpf)
                if sucesso:
                    st.success(mensagem)
                    # Seleciona automaticamente a nova conta
                    st.session_state.conta_atual = nova_conta
                    st.rerun()
                else:
                    st.error(mensagem)
            else:
                st.error("Informe o CPF!")
    
    elif sub_opcao == "Listar Contas":
        st.subheader("Contas Cadastradas")
        lista_contas = banco.listar_contas()
        st.text(lista_contas)
    
    elif sub_opcao == "Selecionar Conta":
        st.subheader("Selecionar Conta Atual")
        
        if banco.contas:
            contas_options = {f"Ag: {conta.agencia} - C/C: {conta.numero_conta} - {conta.usuario.nome}": conta 
                             for conta in banco.contas}
            conta_selecionada = st.selectbox("Selecione uma conta:", list(contas_options.keys()))
            
            if st.button("Selecionar Conta"):
                st.session_state.conta_atual = contas_options[conta_selecionada]
                st.success(f"Conta de {st.session_state.conta_atual.usuario.nome} selecionada!")
                st.rerun()
        else:
            st.warning("Nenhuma conta cadastrada!")

# Informações da conta atual
if conta_atual:
    st.sidebar.success(f"Conta Atual: {conta_atual.usuario.nome}")
    st.sidebar.info(f"Saldo: R$ {conta_atual.saldo:.2f}")
else:
    st.sidebar.warning("Nenhuma conta selecionada")