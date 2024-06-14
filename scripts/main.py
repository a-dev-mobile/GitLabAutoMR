import re
import argparse
from git import Repo, GitCommandError, Actor
import gitlab
import os
from prettytable import PrettyTable, ALL
import tempfile

def format_path(path):
    """Форматирует путь с прямыми слэшами."""
    return path.replace("\\", "/")

def print_table(rows):
    table = PrettyTable()
    table.hrules = ALL
    table.align = "l"
    table.header = False
    for key, value in rows:
        table.add_row([key, value])
    print(table)

def get_project_name(proj_path):
    """Получает название проекта из последней папки в пути"""
    return os.path.basename(os.path.normpath(proj_path))

def configure_environment(cert_content):
    """Настраивает окружение"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as temp_cert_file:
        temp_cert_file.write(cert_content.encode())
        temp_cert_path = temp_cert_file.name
    os.environ['REQUESTS_CA_BUNDLE'] = temp_cert_path

def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description="Скрипт для автоматизации создания веток и Merge Request в GitLab.")
    parser.add_argument("--proj_path", required=True, help="Путь к проекту.")
    parser.add_argument("--jira_task_id", required=True, help="ID задачи в Jira.")
    parser.add_argument("--jira_task_name", required=True, help="Имя задачи в Jira.")
    parser.add_argument("--initial_commit_msg", default="first commit", help="Сообщение первого коммита.")
    parser.add_argument("--task_desc_en", required=True, help="Описание задачи на английском.")
    parser.add_argument("--branch_kind", default="feature", help="Тип ветки (feature, hotfix, bugfix, release).")
    parser.add_argument("--base_branch", default="dev", help="Целевая ветка.")
    parser.add_argument("--gl_proj_id", type=int, required=True, help="ID проекта в GitLab.")
    parser.add_argument("--gl_base_url", default="https://gitlab.com/", help="Базовый URL GitLab.")
    parser.add_argument("--gl_token", required=True, help="Токен доступа GitLab.")
    parser.add_argument("--author_name", required=True, help="Имя автора для коммитов и Merge Request.")
    parser.add_argument("--author_email", required=True, help="Email автора для коммитов и Merge Request.")
    parser.add_argument("--mr_desc_file", default=".gitlab/merge_request_templates/Default.md", help="Путь к файлу с описанием Merge Request.")
    return parser.parse_args()

def validate_arguments(args):
    """Проверяет аргументы командной строки на корректность"""
    if not args.jira_task_id and not args.task_desc_en:
        raise ValueError("И jira_task_id, и task_desc_en пустые.")

    if args.task_desc_en and not re.match(r'^[a-z0-9_]+$', args.task_desc_en):
        raise ValueError("task_desc_en должно содержать только латинские буквы в нижнем регистре, цифры и нижние подчеркивания.")

def generate_branch_name(args):
    """Генерирует имя новой ветки на основе аргументов"""
    if not args.jira_task_id:
        return f"{args.branch_kind}/{args.task_desc_en}-short", f"[{args.branch_kind.capitalize()}] {args.jira_task_name}"
    elif args.task_desc_en:
        return f"{args.branch_kind}/{args.jira_task_id}_{args.task_desc_en}-short", f"[{args.branch_kind.capitalize()}][{args.jira_task_id}] {args.jira_task_name}"
    else:
        return f"{args.branch_kind}/{args.jira_task_id}-short", f"[{args.branch_kind.capitalize()}][{args.jira_task_id}] {args.jira_task_name}"

def branch_exists(repo, branch_name):
    """Проверяет существование ветки локально и на удаленных репозиториях"""
    local_exists = False
    remote_exists = False

    try:
        repo.git.rev_parse("--verify", f"refs/heads/{branch_name}")
        print(f"✔ Локальная ветка '{branch_name}' существует.")
        local_exists = True
    except GitCommandError:
        print(f"✘ Локальная ветка '{branch_name}' не существует.")

    for remote in repo.remotes:
        try:
            branches = repo.git.ls_remote("--heads", remote.name, branch_name)
            if branches:
                print(f"✔ Удаленная ветка '{branch_name}' существует на удаленном '{remote.name}'.")
                remote_exists = True
        except GitCommandError:
            print(f"✘ Не удалось проверить удаленную ветку '{branch_name}' на удаленном '{remote.name}'.")

    if local_exists and remote_exists:
        return "локально и на удаленном репозитории"
    elif local_exists:
        return "локально"
    elif remote_exists:
        return "на удаленном репозитории"
    else:
        print(f"✘ Ветка '{branch_name}' не найдена ни локально, ни на удаленных репозиториях.")
        return False

def mr_exists(project, branch_name):
    """Проверяет существование Merge Request для ветки"""
    mrs = project.mergerequests.list(state='opened', source_branch=branch_name)
    return len(mrs) > 0, mrs[0].web_url if mrs else None

def main():
    cert_content = os.getenv("CERTIFICATE")
    if cert_content is None:
        raise RuntimeError("CERTIFICATE не найден в переменных окружения.")

    configure_environment(cert_content)

    args = parse_arguments()
    validate_arguments(args)

    project_name = get_project_name(args.proj_path)
    new_branch_name, mr_title = generate_branch_name(args)

    repo = Repo(args.proj_path)
    current_branch_name = repo.active_branch.name

    if repo.is_dirty(untracked_files=True):
        user_response = input(f"Целевая ветка '{args.base_branch}' содержит изменения. Продолжить? (y/n): ")
        if user_response.lower() != 'y':
            raise RuntimeError("Процесс прерван пользователем.")
    
    if current_branch_name != args.base_branch:
        raise RuntimeError(f"Вы не на ветке '{args.base_branch}'. Вы на ветке '{current_branch_name}'. Необходимо переключиться на целевую ветку '{args.base_branch}' для продолжения.")

    gl = gitlab.Gitlab(args.gl_base_url, private_token=args.gl_token)
    project = gl.projects.get(args.gl_proj_id)

    location = branch_exists(repo, new_branch_name)
    if location:
        mr_exist, mr_url = mr_exists(project, new_branch_name)
        if mr_exist:
            raise RuntimeError(f"Merge Request для ветки '{new_branch_name}' уже существует. URL: {mr_url}")
        else:
            raise RuntimeError(f"Ветка {new_branch_name} уже существует {location}.")

    print("\n--- Подтверждение создания ветки и отправки на удаленный репозиторий ---\n")
    branch_info = [
        ("Project", project_name),
        ("Branch", new_branch_name),
        ("Author", args.author_name),
        ("Email", args.author_email),
    ]
    print_table(branch_info)
    
    confirm_branch = input("Вы согласны создать и отправить ветку с такими данными? (y/n): ")
    if confirm_branch.lower() != "y":
        raise RuntimeError("Создание ветки и отправка  - отменены пользователем.")

    new_branch_ref = repo.create_head(new_branch_name)
    new_branch_ref.checkout()
    repo.remote().push(refspec=f"{new_branch_name}:{new_branch_name}")
    print(f"✔ Ветка '{new_branch_name}' успешно создана и отправлена в удаленный репозиторий.")

    mr_desc_path = os.path.join(args.proj_path, args.mr_desc_file)
    mr_description = None
    if os.path.exists(mr_desc_path):
        with open(mr_desc_path, 'r', encoding='utf-8') as file:
            mr_description = file.read()
    else:
        print(f"Файл для описания Merge Request по пути '{args.mr_desc_file}' не найден.")

    
    print("\n--- Подтверждение создания Merge Request ---\n")
    mr_info = [
        ("Project", project_name),
        ("Title", mr_title),
        ("Target branch", args.base_branch),
        ("Description", mr_description if mr_description else "Описание отсутствует."),
    ]
    print_table(mr_info)
    confirm_mr = input("Согласны ли вы отправить Merge Request с такими данными? (y/n): ")
    if confirm_mr.lower() != "y":
        raise RuntimeError("Merge Request отменен пользователем.")
    mr_data = {
        "source_branch": new_branch_name,
        "target_branch": args.base_branch,
        "title": mr_title,
        "author": {
            "name": args.author_name,
            "email": args.author_email
        },
        "squash": True,
    }
    if mr_description:
        mr_data["description"] = mr_description
    mr = project.mergerequests.create(mr_data)
    print("\n✔ Merge Request создан")
    print("")
    print(mr.title)
    print(mr.web_url)

if __name__ == "__main__":
    main()
