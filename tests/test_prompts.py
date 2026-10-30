"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert isinstance(prompt["system_prompt"], str)
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt["system_prompt"]
        assert re.search(r"Você é (um|uma) ", system_prompt), "Persona não definida com 'Você é um...'"
        assert "Product Manager" in system_prompt

    def test_prompt_mentions_format(self, prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt["system_prompt"]
        assert "User Story" in system_prompt
        # Template padrão: Como um... eu quero... para que...
        for part in ("Como um", "eu quero", "para que"):
            assert part in system_prompt, f"Template de User Story sem '{part}'"
        # Critérios de aceitação no formato Dado/Quando/Então
        for part in ("Critérios de Aceitação", "Dado que", "Quando", "Então"):
            assert part in system_prompt, f"Formato de critérios sem '{part}'"

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt["system_prompt"]
        examples = re.findall(r"^## Exemplo \d+", system_prompt, flags=re.MULTILINE)
        assert len(examples) >= 2, f"Few-shot exige ao menos 2 exemplos, encontrados: {len(examples)}"
        assert system_prompt.count("Entrada:") >= len(examples)
        assert system_prompt.count("Saída:") >= len(examples)

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        full_text = yaml.safe_dump(prompt, allow_unicode=True)
        assert "[TODO]" not in full_text
        assert "TODO" not in full_text

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2, f"Mínimo de 2 técnicas, encontradas: {len(techniques)}"
        assert "Few-shot Learning" in techniques, "Few-shot Learning é obrigatório"

    def test_prompt_structure_is_valid(self, prompt):
        """Valida a estrutura completa com o validador de utils.py."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors

    def test_bug_report_only_in_user_prompt(self, prompt):
        """O relato entra só pela mensagem do usuário (a v1 duplicava no system prompt)."""
        assert "{bug_report}" in prompt["user_prompt"]
        assert "{bug_report}" not in prompt["system_prompt"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
