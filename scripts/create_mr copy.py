import re
import argparse
from git import Repo, GitCommandError, Actor
import gitlab
import os
from prettytable import PrettyTable, ALL

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

def main():
    # Установите путь к сертификату
    cert_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../cert/cert.pem'))
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path

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
    parser.add_argument("--create_mr", action='store_true', help="Создать Merge Request после создания ветки.")
    parser.add_argument("--author_name", required=True, help="Имя автора для коммитов и Merge Request.")
    parser.add_argument("--author_email", required=True, help="Email автора для коммитов и Merge Request.")
    parser.add_argument("--mr_desc_file", default=".gitlab/merge_request_templates/Default.md", help="Путь к файлу с описанием Merge Request.")

    args = parser.parse_args()

    project_name = get_project_name(args.proj_path)

    if not args.jira_task_id and not args.task_desc_en:
        raise ValueError("И jira_task_id, и task_desc_en пустые.")

    if args.task_desc_en:
        if not re.match(r'^[a-z0-9_]+$', args.task_desc_en):
            raise ValueError("task_desc_en должно содержать только латинские буквы в нижнем регистре, цифры и нижние подчеркивания.")

    if not args.jira_task_id:
        new_branch_name = f"{args.branch_kind}/{args.task_desc_en}-short"
        mr_title = f"[{args.branch_kind.capitalize()}] {args.jira_task_name}"
    elif args.task_desc_en:
        new_branch_name = f"{args.branch_kind}/{args.jira_task_id}_{args.task_desc_en}-short"
        mr_title = f"[{args.branch_kind.capitalize()}][{args.jira_task_id}] {args.jira_task_name}"
    else:
        new_branch_name = f"{args.branch_kind}/{args.jira_task_id}-short"
        mr_title = f"[{args.branch_kind.capitalize()}][{args.jira_task_id}] {args.jira_task_name}"

    repo = Repo(args.proj_path)
    current_branch_name = repo.active_branch.name

    gl = gitlab.Gitlab(args.gl_base_url, private_token=args.gl_token)
    project = gl.projects.get(args.gl_proj_id)

    def branch_exists(branch_name):
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

    def mr_exists(branch_name):
        mrs = project.mergerequests.list(state='opened', source_branch=branch_name)
        return len(mrs) > 0, mrs[0].web_url if mrs else None

    location = branch_exists(new_branch_name)
    if location:
        mr_exist, mr_url = mr_exists(new_branch_name)
        if mr_exist:
            print(f"Merge Request для ветки '{new_branch_name}' уже существует. URL: {mr_url}")
            raise RuntimeError(f"Ветка {new_branch_name} уже существует {location} и существует Merge Request. Пожалуйста, измените название ветки, используя jira_task_id, task_desc_en и branch_kind.")
        else:
            # print("\n--- Подтверждение создания Merge Request ---\n")
            # mr_info = [
            #     ("Project", project_name),
            #     ("Title", mr_title),
            #     ("Target branch", args.base_branch),
            #     ("Description", "Описание отсутствует."),
            # ]
            # print_table(mr_info)
            confirm_mr = input(f"Ветка {new_branch_name} уже существует {location}, но Merge Request не существует. Хотите создать Merge Request? (y/n): ")
            if confirm_mr.lower() == 'y':
                args.create_mr = True
            else:
                raise RuntimeError("Создание Merge Request отменено пользователем.")

    # Проверка, если текущая ветка равна создаваемой и ветки нет в удалённом репозитории
    if current_branch_name == new_branch_name and not branch_exists(new_branch_name):
        create_mr_response = input(f"Текущая ветка '{current_branch_name}' совпадает с создаваемой веткой '{new_branch_name}', и ветки нет в удалённом репозитории. Хотите сразу создать Merge Request? (y/n): ")
        if create_mr_response.lower() == 'y':
            args.create_mr = True

    if current_branch_name != args.base_branch:
        switch_branch = input(f"Вы не на ветке '{args.base_branch}'. Вы на ветке '{current_branch_name}'. Хотите переключиться на '{args.base_branch}'? (y/n): ")
        if switch_branch.lower() == 'y':
            repo.git.checkout(args.base_branch)
            print(f"Переключение на ветку '{args.base_branch}' успешно.")
        else:
            raise RuntimeError(f"Необходимо переключиться на ветку '{args.base_branch}' для продолжения.")

    def check_and_confirm_files():
        changed_files = [os.path.abspath(item.a_path) for item in repo.index.diff(None)]
        staged_files = [os.path.abspath(item.a_path) for item in repo.index.diff("HEAD")]

        # if not changed_files and not staged_files:
            # create_branch = input(f"Нет изменений для коммита. Хотите создать новую ветку '{new_branch_name}' без коммита? (y/n): ")
            # if create_branch.lower() != "y":
                # raise RuntimeError("Создание ветки без изменений отменено.")
            # else:
                # return []

        if staged_files:
            formatted_staged_files = [format_path(f) for f in staged_files]
            print_table([("Файл", f) for f in formatted_staged_files])
            continue_response = input("Хотите продолжить с этими добавленными файлами? (y/n): ")
            if continue_response.lower() != "y":
                raise RuntimeError("Прерывание. Пожалуйста, добавьте необходимые файлы и запустите скрипт снова.")
        else:
            formatted_changed_files = [format_path(f) for f in changed_files]
            print_table([("Файл", f) for f in formatted_changed_files])
            continue_response = input("Нет добавленных файлов для коммита. Хотите добавить все измененные файлы? (y/n): ")
            if continue_response.lower() != "y":
                raise RuntimeError("Прерывание. Пожалуйста, добавьте необходимые файлы и запустите скрипт снова.")
            else:
                repo.git.add(A=True)
                print(f"✔ Все измененные файлы добавлены для коммита.")

        if not repo.index.diff("HEAD"):
            raise RuntimeError("Нет добавленных файлов для коммита. Пожалуйста, добавьте файлы перед запуском скрипта.")

        return staged_files if staged_files else changed_files

    files_to_commit = check_and_confirm_files()
    formatted_files_to_commit = [format_path(f) for f in files_to_commit]
    
    if not args.create_mr:
        print("\n--- Подтверждение создания ветки и отправки на удаленный репозиторий ---\n")
        branch_info = [
            ("Project", project_name),
            ("Branch", new_branch_name),
            ("Author", args.author_name),
            ("Email", args.author_email),
        ]
        if files_to_commit:
            branch_info.append(("Добавленные файлы", "\n".join(formatted_files_to_commit)))
        print_table(branch_info)
        confirm_branch = input("Вы согласны создать и отправить ветку с такими данными? (y/n): ")
        if confirm_branch.lower() != "y":
            raise RuntimeError("Создание ветки и отправка отменены пользователем.")

    new_branch_ref = repo.create_head(new_branch_name)
    new_branch_ref.checkout()
    if files_to_commit:
        author = Actor(args.author_name, args.author_email)
        repo.index.commit(args.initial_commit_msg, author=author)
    repo.remote().push(refspec=f"{new_branch_name}:{new_branch_name}")
    print(f"✔ Ветка '{new_branch_name}' успешно создана и отправлена в удаленный репозиторий.{' (без коммитов)' if not files_to_commit else ''}")

    mr_desc_path = os.path.join(args.proj_path, args.mr_desc_file)
    mr_description = None
    if os.path.exists(mr_desc_path):
        with open(mr_desc_path, 'r', encoding='utf-8') as file:
            mr_description = file.read()
    else:
        print(f"Файл для описания Merge Request по пути '{args.mr_desc_file}' не найден.")

    if args.create_mr:
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

        author = gl.users.get(mr.author['id'])

        print("\n✔ Merge Request создан")
        print("\n")
        print(mr.title)
        print(mr.web_url)

if __name__ == "__main__":
    main()
