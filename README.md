# 🚢 NaviFlow



**NaviFlow** é um sistema web responsivo desenvolvido para visualização em tempo real da movimentação de navios no terminal TECONT. O projeto apresenta os dados em uma interface limpa e adaptável, facilitando o acompanhamento de atracações, saídas, manobras e informações detalhadas de cada navio.

---

## 📋 Funcionalidades

- 📆 Visualização de datas e horários de atracação/saída
- 🚢 Detalhes do navio: nome, IMO, tipo, calado e beço
- ⚓ Informações sobre a manobra (entrada ou saída)
- 📱 Interface responsiva: apresentação em formato vertical no mobile
- 📊 Atualização automática com hora da última sincronização
- 🌊 Alerta sobre status da barra (restrita ou aberta)

---

## 🖼️ Exemplo da Interface

> Exibição clara e responsiva para web e dispositivos móveis.

<p align="center">
  <img src="caminho/para/sua/imagem-de-exemplo.png" alt="Exemplo da Interface NaviFlow" width="700">
</p>

---

## 🛠️ Tecnologias Utilizadas

- HTML5 e CSS3
- [Materialize CSS](https://materializecss.com/) – Framework CSS responsivo
- Jinja2 (templating engine do Flask)
- Flask (para renderização dos dados e backend)
- Python 3

---

## 🚀 Como Rodar o Projeto

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/naviflow.git
```
2. Acesse o diretório:
```bash
cd naviflow
```
3. Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```
4. Instale as dependências:

```bash
pip install -r requirements.txt
```

5. Execute o aplicativo:

```bash
flask run
```

## 📱 Responsividade

No desktop, os dados são exibidos em formato de tabela horizontal.  
No mobile, a exibição muda para **formato vertical por navio**, garantindo leitura fácil em telas pequenas.

----------

## 📄 Licença

Este projeto está licenciado sob a **MIT License** – veja o arquivo LICENSE para mais detalhes.

----------

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir uma issue ou um pull request.
