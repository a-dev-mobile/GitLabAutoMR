#!/bin/bash

# Путь к исполняемому файлу
EXECUTABLE="/Users/trofimovdi/CLOUD/notes/GitLabAutoMR/dist/gitlab_auto_mr"

# Аргументы
PROJ_PATH="/Users/trofimovdi/Documents/projects/SupApp/microservices/api-motivation"
JIRA_TASK_ID="SUPAPP-00"
JIRA_TASK_NAME="Тестирую авто создание MR"
INITIAL_COMMIT_MSG="first commit"
TASK_DESC_EN="test_auto_mr2"
# feature release bugfix hotfix 
BRANCH_KIND="bugfix"
BASE_BRANCH="dev"
GL_PROJ_ID="169398"
GL_BASE_URL="https://gitlab.services.mts.ru/"
GL_TOKEN="AA-RJBHyuzgLYGxE7buK"
AUTHOR_EMAIL="trofimovdi@mts.ru"
AUTHOR_NAME="Трофимов Дмитрий Игоревич"
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
