"""Validador de dependencias em projeto dotnet
    Executar esse script dentro da pasta onde está o arquivo .sln
"""
import argparse
import subprocess
import json
import sys
import os


RED = '\033[91m'    # Vermelho
GREEN = '\033[92m'  # Verde
RESET = '\033[0m'   # Resetar a cor

# Padrões
FRAMEWORK_PADRAO = "net8.0"
PACOTES_ESPERADOS = [
    {
        "projeto": "TestePrometheusGrafana.csproj",
        "nome_pacote": "Swashbuckle.AspNetCore",
        "usar_ultima_versao": True
    },
    {
        "projeto": "UnitTests.csproj",
        "nome_pacote": "coverlet.collector",
        "usar_ultima_versao": False
    }
]


# Função para executar um comando e carregar o JSON da saída
def run_command_shell_json(command):
    """Função executa um comando shell que o retorno é um json."""
    try:
        # Executa o comando e captura a saída
        result = subprocess.run(
            command, shell=True, check=True,
            stdout=subprocess.PIPE, text=True)

        # Carrega a saída JSON
        return json.loads(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o comando '{command}': {e}")
        return None

    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON do comando '{command}': {e}")
        return None



def valida_dependencias_projeto():
    """Valida as dependencias do projeto.
    Retorna os projetos que não estão com o framework esperado
    Retorna os projetos que não estão usando uma dependencias esperada"""

    lista_pacotes_instalados = run_command_shell_json(
        'dotnet list package --format json')

    lista_projetos = lista_pacotes_instalados["projects"]
    lista_projetos_com_framework_errada = []
    pacotes_esperados_nao_encontrados = list(PACOTES_ESPERADOS)

    for projeto in lista_projetos:
        nome_projeto = os.path.basename(projeto["path"])
        lista_frameworks = projeto["frameworks"]

        for project_framework in lista_frameworks:
            if project_framework["framework"] != FRAMEWORK_PADRAO:
                lista_projetos_com_framework_errada.append(nome_projeto)

            top_level_packages = project_framework["topLevelPackages"]
            for top_level_package in top_level_packages:
                nome_pacote = top_level_package["id"]

                index_corrente = 0
                index_encontrado = -1
                for pacote_esperado in pacotes_esperados_nao_encontrados:
                    if pacote_esperado['projeto'] == nome_projeto and \
                            pacote_esperado['nome_pacote'] == nome_pacote:
                        index_encontrado = index_corrente
                    index_corrente = index_corrente + 1
                if index_encontrado >= 0:
                    del pacotes_esperados_nao_encontrados[index_encontrado]

    return {
        "lista_pacotes_instalados":
            lista_pacotes_instalados,
        "lista_projetos_com_framework_errada":
            lista_projetos_com_framework_errada,
        "pacotes_esperados_nao_encontrados":
            pacotes_esperados_nao_encontrados
    }


def valida_dependencias_nao_atualizadas():
    """Valida dependencias não atualizadas"""
    # Executa os comandos e carrega os JSONs
    lista_pacotes_desatalizados = run_command_shell_json(
        'dotnet list package --outdated --format json')

    lista_projetos = lista_pacotes_desatalizados["projects"]
    lista_projetos_com_framework_errada = []
    pacotes_esperados_nao_encontrados = list(filter(
        lambda item: item['usar_ultima_versao'], PACOTES_ESPERADOS))
    pacotes_deveriam_esta_atualizados = []

    for projeto in lista_projetos:
        nome_projeto = os.path.basename(projeto["path"])
        lista_frameworks = projeto["frameworks"]

        for project_framework in lista_frameworks:
            if project_framework["framework"] != FRAMEWORK_PADRAO:
                lista_projetos_com_framework_errada.append(nome_projeto)

            top_level_packages = project_framework["topLevelPackages"]
            for top_level_package in top_level_packages:
                nome_pacote = top_level_package["id"]

                for pacote_esperado in pacotes_esperados_nao_encontrados:
                    if pacote_esperado['projeto'] == nome_projeto and \
                            pacote_esperado['nome_pacote'] == nome_pacote:
                        pacotes_deveriam_esta_atualizados.append(
                            {
                                "projeto":
                                    pacote_esperado['projeto'],
                                "nome_pacote":
                                    pacote_esperado['nome_pacote'],
                                "versao_no_projeto":
                                    top_level_package['resolvedVersion'],
                                "versao_esperada":
                                    top_level_package['latestVersion'],
                            }
                        )
    return pacotes_deveriam_esta_atualizados


def print_error(msg):
    """Print com a cor vermelha e com prefixo "Error:"""
    print(f"{RED}Error: {msg}{RESET}")


def print_sucess(msg):
    """Print com a cor verde e com prefixo "Success:"""
    print(f"{GREEN}Success: {msg}{RESET}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exemplo de script com parâmetros nomeados.")

    # Adiciona os parâmetros nomeados
    parser.add_argument(
        "--tipo_projeto",
        type=str,
        required=True,
        help="Tipo do projeto (BFF, API, MFE)")

    # Parseia os argumentos
    args = parser.parse_args()

    print(f"Parametros: {args}")
    print("\n-\n")

    # Exemplo de manipulação dos dados carregados
    validacoes_pacotes = valida_dependencias_projeto()
    validacoes_versao = valida_dependencias_nao_atualizadas()

    print("Lista de Pacotes Instalados:")
    print(validacoes_pacotes["lista_pacotes_instalados"])

    print("\n-\n")

    existe_erro = False
    if len(validacoes_pacotes["lista_projetos_com_framework_errada"]) > 0:
        existe_erro = True
        print_error(f"Projetos com framework diferente de '{FRAMEWORK_PADRAO}'" +
                    str(validacoes_pacotes["lista_projetos_com_framework_errada"]))
    else:
        print_sucess("Ok - Não existe projetos com framework " +
                    f"diferente de '{FRAMEWORK_PADRAO}'.")

    if len(validacoes_pacotes["pacotes_esperados_nao_encontrados"]) > 0:
        existe_erro = True
        print_error("Pacotes que não foram encontrados: " +
                    str(validacoes_pacotes["pacotes_esperados_nao_encontrados"]))
    else:
        print_sucess("Ok - Todos os pacotes esperados foram encontrados")

    if len(validacoes_versao) > 0:
        existe_erro = True
        print_error("Pacotes com a versão desatualizda " + str(validacoes_versao))
    else:
        print_sucess("Ok - Todos os pacotes estão com as versão esperadas")

    sys.exit(existe_erro if 1 else 0)
