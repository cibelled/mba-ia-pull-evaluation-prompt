"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
REQUIRED_VARIABLE = "bug_report"


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_id = f"{username}/{prompt_name}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])

    techniques = prompt_data.get("techniques_applied", [])
    tags = list(dict.fromkeys(
        prompt_data.get("tags", [])
        + [prompt_data.get("version", "")]
        + [t.lower().replace(" ", "-") for t in techniques]
    ))
    tags = [t for t in tags if t]

    description = (
        f"{prompt_data['description']}. "
        f"Técnicas aplicadas: {', '.join(techniques)}."
    )

    readme = (
        f"# {prompt_name}\n\n"
        f"{prompt_data['description']}.\n\n"
        f"- Versão: {prompt_data.get('version', '')}\n"
        f"- Variável de entrada: `{{{REQUIRED_VARIABLE}}}`\n"
        f"- Técnicas aplicadas: {', '.join(techniques)}\n"
    )

    print(f"Fazendo push: {prompt_id}")
    try:
        client = Client()
        url = client.push_prompt(
            prompt_id,
            object=prompt,
            is_public=True,
            description=description,
            readme=readme,
            tags=tags,
        )
    except Exception as e:
        # O Hub recusa um commit idêntico ao último: nesse caso o prompt já está publicado
        if "Nothing to commit" in str(e):
            print("   ✓ Prompt sem alterações desde o último push (já publicado)")
            return True
        print(f"❌ Erro ao fazer push do prompt: {e}")
        return False

    print(f"   ✓ Push concluído (público)")
    print(f"   ✓ Tags: {', '.join(tags)}")
    print(f"   ✓ {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)

    user_prompt = prompt_data.get("user_prompt", "")
    if not user_prompt.strip():
        errors.append("user_prompt está vazio")
    elif f"{{{REQUIRED_VARIABLE}}}" not in user_prompt:
        errors.append(f"user_prompt não contém a variável {{{REQUIRED_VARIABLE}}}")

    # O bug_report deve entrar só uma vez, pela mensagem do usuário (problema da v1)
    if f"{{{REQUIRED_VARIABLE}}}" in prompt_data.get("system_prompt", ""):
        errors.append(f"system_prompt não deve conter {{{REQUIRED_VARIABLE}}} (duplicaria o relato)")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_KEY not in data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH.name}")
        return 1

    prompt_data = data[PROMPT_KEY]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    return 0 if push_prompt_to_langsmith(PROMPT_KEY, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
