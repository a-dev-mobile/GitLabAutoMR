import re
import argparse
from git import Repo, GitCommandError
import gitlab

def main():
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

    args = parser.parse_args()

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
    if current_branch_name != args.base_branch:
        raise RuntimeError(f"Вы не на ветке '{args.base_branch}'. Вы на ветке '{current_branch_name}'. Пожалуйста, переключитесь на '{args.base_branch}' и попробуйте снова.")    

    def branch_exists(branch_name):
        try:
            repo.git.rev_parse("--verify", f"refs/heads/{branch_name}")
            print(f"Локальная ветка '{branch_name}' существует.")
            return True
        except GitCommandError:
            print(f"Локальная ветка '{branch_name}' не существует.")

        for remote in repo.remotes:
            try:
                branches = repo.git.ls_remote("--heads", remote.name, branch_name)
                if branches:
                    print(f"Удаленная ветка '{branch_name}' существует на удаленном '{remote.name}'.")
                    return True
            except GitCommandError:
                print(f"Не удалось проверить удаленную ветку '{branch_name}' на удаленном '{remote.name}'.")
                continue

        return False

    if branch_exists(new_branch_name):
        raise RuntimeError(f"Ветка {new_branch_name} уже существует.")

    def check_and_confirm_files():
        changed_files = [item.a_path for item in repo.index.diff(None)]
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]

        if not changed_files and not staged_files:
            raise RuntimeError(f"Нет изменений для коммита в ветке '{current_branch_name}'. Пожалуйста, добавьте файлы перед запуском скрипта.")

        if staged_files:
            print(f"Добавленные файлы: {staged_files}")
            continue_response = input("Хотите продолжить с этими добавленными файлами? (y/n): ")
            if continue_response.lower() != "y":
                raise RuntimeError("Прерывание. Пожалуйста, добавьте необходимые файлы и запустите скрипт снова.")
        else:
            print(f"Измененные файлы: {changed_files}")
            continue_response = input("Нет добавленных файлов для коммита. Хотите добавить все измененные файлы? (y/n): ")
            if continue_response.lower() != "y":
                raise RuntimeError("Прерывание. Пожалуйста, добавьте необходимые файлы и запустите скрипт снова.")
            else:
                repo.git.add(A=True)

        if not repo.index.diff("HEAD"):
            raise RuntimeError("Нет добавленных файлов для коммита. Пожалуйста, добавьте файлы перед запуском скрипта.")

        return staged_files if staged_files else changed_files

    files_to_commit = check_and_confirm_files()
    new_branch_ref = repo.create_head(new_branch_name)
    new_branch_ref.checkout()
    repo.index.commit(args.initial_commit_msg)
    repo.remote().push(refspec=f"{new_branch_name}:{new_branch_name}")

    gl = gitlab.Gitlab(args.gl_base_url, private_token=args.gl_token)
    project = gl.projects.get(args.gl_proj_id)
    mr = project.mergerequests.create({
        "source_branch": new_branch_name,
        "target_branch": args.base_branch,
        "title": mr_title,
        "squash": True,
    })

    author = gl.users.get(mr.author['id'])
    author_email = author.email if hasattr(author, 'email') else "Email отсутствует"

    print("Merge Request создан")
    print("")
    print(mr.title)
    print(mr.web_url)

    print("\n--- Общая информация ---")
    print(f"Создана новая ветка: {new_branch_name}")
    print(f"Добавлены файлы: {files_to_commit}")
    print(f"Целевая ветка: {args.base_branch}")
    print(f"Merge Request заголовок: {mr.title}")
    print(f"URL Merge Request: {mr.web_url}")
    print(f"Описание Merge Request: {mr.description if mr.description else 'Описание отсутствует.'}")
    print(f"Автор Merge Request: {author.name}")
    print(f"Email автора Merge Request: {author_email}")
    print(f"Дата создания Merge Request: {mr.created_at}")
    print("------------------------")

if __name__ == "__main__":
    main()
