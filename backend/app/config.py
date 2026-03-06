import os
from dotenv import load_dotenv

load_dotenv()


from typing import List


class Settings:
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY", "")
    NOTION_ROOT_PAGE_ID: str = os.getenv("NOTION_ROOT_PAGE_ID", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPOS: List[str] = [
        r.strip()
        for r in os.getenv("GITHUB_REPOS", "").split(",")
        if r.strip()
    ]

    # Database IDs — populated after setup
    PROJECTS_DB_ID: str = os.getenv("PROJECTS_DB_ID", "")
    TASKS_DB_ID: str = os.getenv("TASKS_DB_ID", "")
    WEEKLY_PLANS_DB_ID: str = os.getenv("WEEKLY_PLANS_DB_ID", "")
    AVAILABILITY_DB_ID: str = os.getenv("AVAILABILITY_DB_ID", "")


settings = Settings()
