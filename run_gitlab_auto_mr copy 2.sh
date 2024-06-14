#!/bin/bash

# Путь к исполняемому файлу
# Укажите полный путь к вашему исполняемому файлу
EXECUTABLE="/path/to/your/executable"

# Аргументы
# Укажите путь к вашему проекту
PROJ_PATH="/path/to/your/project"
# Укажите ID задачи в JIRA
JIRA_TASK_ID="YOUR_JIRA_TASK_ID"
# Укажите имя задачи в JIRA
JIRA_TASK_NAME="YOUR_JIRA_TASK_NAME"
# Укажите сообщение для первого коммита
INITIAL_COMMIT_MSG="your_initial_commit_message"
# Краткое описание задачи на английском языке
TASK_DESC_EN="your_task_description_in_english"
# Укажите тип ветки (например, feature, release, bugfix, hotfix)
BRANCH_KIND="your_branch_kind"
# Укажите базовую ветку (например, master, dev)
BASE_BRANCH="your_base_branch"
# Укажите ID проекта в GitLab
GL_PROJ_ID="your_gitlab_project_id"
# Укажите базовый URL GitLab
GL_BASE_URL="https://gitlab.services.mts.ru/"
# Укажите ваш токен доступа к GitLab
GL_TOKEN="your_gitlab_access_token"
# Укажите ваш email
AUTHOR_EMAIL="example@mts.ru"
# Укажите ваше имя (полное на русском ФИО)
AUTHOR_NAME="Your Name"
# Укажите относительный путь к файлу шаблона описания MR
MR_DESC_FILE=".gitlab/merge_request_templates/Default.md"

# Запуск скрипта с аргументами
"$EXECUTABLE" --proj_path "$PROJ_PATH" \
              --jira_task_id "$JIRA_TASK_ID" \
              --jira_task_name "$JIRA_TASK_NAME" \
              --initial_commit_msg "$INITIAL_COMMIT_MSG" \
              --task_desc_en "$TASK_DESC_EN" \
              --branch_kind "$BRANCH_KIND" \
              --base_branch "$BASE_BRANCH" \
              --gl_proj_id "$GL_PROJ_ID" \
              --gl_base_url "$GL_BASE_URL" \
              --gl_token "$GL_TOKEN" \
              --author_email "$AUTHOR_EMAIL" \
              --author_name "$AUTHOR_NAME" \
              --mr_desc_file "$MR_DESC_FILE"
