# BACKEND_MONITORAMENTO – Solar Monitoring Platform (FastAPI)

Este é o backend de uma plataforma completa para monitoramento de usinas solares fotovoltaicas, com foco em performance energética, integração com APIs de fabricantes e geração de relatórios personalizados.

## Funcionalidades

- Autenticação com JWT (usuário/admin)
- Integração com APIs de fabricantes (Sungrow, Deye, Huawei)
- Cálculo de performance (1 dia, 7 dias, 30 dias) com cache individual por cliente
- Armazenamento de projeções mensais por usina
- Multiusuário com separação de dados por cliente
- Geração de relatórios em PDF
- Banco de dados PostgreSQL
- Background tasks e caching com Redis

## Tecnologias Utilizadas

- Python 3.11
- FastAPI
- PostgreSQL + SQLAlchemy
- Redis
- Pydantic
- JWT Authentication
- Uvicorn
- Docker / Railway

## Estrutura do Projeto

backend/
├── app.py # Ponto de entrada principal (FastAPI)
├── clients/ # Integrações com APIs externas
│ ├── isolarcloud_client.py
│ ├── deye_client.py
│ └── huawei_client.py
├── routes/ # Rotas da aplicação
│ ├── usinas.py
│ ├── integracoes.py
│ └── auth.py
├── services/ # Lógica de negócio (performance, projeções, alarmes)
├── modelos.py # Modelos ORM (SQLAlchemy)
├── esquemas.py # Esquemas Pydantic
├── utils.py # Funções auxiliares (hashing, horário, autenticação)
└── database.py # Conexão com o banco de dados

bash
Copiar
Editar

## Endpoints Principais

| Método | Rota                             | Descrição |
|--------|----------------------------------|-----------|
| POST   | `/login`                         | Login e geração de token |
| GET    | `/usina`                         | Lista as usinas do cliente |
| GET    | `/geracao_diaria`               | Retorna geração do dia |
| GET    | `/performance_30dias`           | Performance dos últimos 30 dias |
| POST   | `/projecoes/salvar_e_recalcular`| Salva projeções mensais e recalcula performance |
| POST   | `/integracoes/`                 | Cria integração com plataforma (ex: Deye, Sungrow) |
| GET    | `/admin/integracoes`            | (Admin) Visualiza integrações por cliente |

## Como rodar localmente

```bash
# Clone o repositório
git clone https://github.com/seuusuario/BACKEND_MONITORAMENTO.git
cd BACKEND_MONITORAMENTO

# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure variáveis de ambiente (crie um .env com suas chaves)

# Rode o servidor
uvicorn app:app --reload
Variáveis de ambiente esperadas (.env.example)
env
Copiar
Editar
SECRET_KEY=suachavesecreta
DATABASE_URL=postgresql://usuario:senha@localhost:5432/monitoramento
REDIS_URL=redis://localhost:6379
Licença
Este projeto é de uso pessoal e experimental, voltado para estudos e demonstração de integração entre engenharia elétrica e desenvolvimento backend.

Para contribuições ou dúvidas, entre em contato ou abra uma issue.

yaml
Copiar
Editar

---

Se quiser, posso criar agora o `README.md` do seu frontend também, seguindo o mesmo estilo profissional. Des