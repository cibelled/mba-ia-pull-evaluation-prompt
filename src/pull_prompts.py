"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _str_representer(dumper, data):
    # Textos com várias linhas saem no estilo bloco (|), legível como o YAML original
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


yaml.add_representer(str, _str_representer)

PROMPT_ID = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt semente do LangSmith Hub e converte para o formato YAML
    usado no projeto (system_prompt, user_prompt e metadados).

    Returns:
        Dicionário pronto para salvar em YAML
    """
    client = Client()

    print(f"Puxando prompt: {PROMPT_ID}")
    prompt = client.pull_prompt(PROMPT_ID, dangerously_pull_public_prompt=True)
    print(f"   ✓ {len(prompt.messages)} mensagem(ns) carregada(s)")

    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        template = message.prompt.template
        message_type = type(message).__name__

        if message_type.startswith("System"):
            system_prompt = template
        elif message_type.startswith("Human"):
            user_prompt = template
        else:
            print(f"   ⚠️  Mensagem ignorada (tipo {message_type})")

    metadata = prompt.metadata or {}

    return {
        PROMPT_KEY: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": "v1",
            "source": PROMPT_ID,
            "commit": metadata.get("lc_hub_commit_hash", ""),
            "input_variables": list(prompt.input_variables),
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        data = pull_prompts_from_langsmith()
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        return 1

    if not save_yaml(data, str(OUTPUT_PATH)):
        return 1

    print(f"   ✓ Prompt salvo em {OUTPUT_PATH.relative_to(OUTPUT_PATH.parent.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
