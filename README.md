# Rommaka Praxis — Gestão de Atividades

Aplicação CRUD em português para cadastrar, editar, concluir e excluir atividades. Foi concebida para correr no navegador e adaptar-se a ecrãs móveis, incluindo o Samsung Galaxy A17.

## Funcionalidades

- Formulário de atividade: lista diária, atividade, setor, subsetor, local, data, horário, passo a passo, comentário e realizado.
- Ao criar, **Salvar** grava e limpa os campos. Na edição, os dados são atualizados e o formulário volta ao modo de novo registo.
- CRUD completo com confirmação antes de excluir.
- Abas para lista diária (primeira/aberta por padrão), todas as atividades, setor, subsetor, data e pontos.
- Links HTTP/HTTPS colados em passo a passo ou comentário são apresentados como links clicáveis.
- **A pontuação só acontece quando o campo “Realizado” está marcado e a atividade está na lista diária.** Cada atividade concluída vale 1 ponto, contado pela data agendada.
- Pontos consultáveis por dia, mês e ano. A mudança do ano começa um período novo em zero sem apagar o histórico: anos anteriores permanecem consultáveis.
- SQLite local, com caminho configurável para pasta do Google Drive.

Setores e subsetores são valores nas atividades e as abas agrupam os registos automaticamente. Para mudar o setor/subsetor de uma atividade, use **Editar**.

## Executar localmente

Requer Python 3.10 ou superior.

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Por padrão, a base fica em `data/rommaka_praxis.sqlite3`.

## Google Colab com Google Drive

Monte o Drive e configure o caminho da base antes de iniciar a aplicação:

```python
from google.colab import drive
drive.mount('/content/drive')
%pip install -r requirements.txt
import os
os.environ['RMP_DB_PATH'] = '/content/drive/MyDrive/RommakaPraxis/atividades.sqlite3'
```

Inicie Streamlit na porta 8501 e exponha essa porta com o mecanismo de túnel que preferir:

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Mantenha o processo ativo enquanto usar o app e não inicie várias instâncias escrevendo simultaneamente no mesmo SQLite.
