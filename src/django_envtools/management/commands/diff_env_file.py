import re
from pathlib import Path

from django.core.management import BaseCommand

from django_envtools import env_variables


class Command(BaseCommand):
    help = "Show differences between your .env file and env variables in your Django settings."

    def handle(self, *args, **options):
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            self.stdout.write(self.style.ERROR(f"{env_path} does not exist."))
            return

        with env_path.open() as f:
            env_lines = f.readlines()

        existing_vars = []
        for line in env_lines:
            if re.match(r"^(#\s)?[_A-Z]+=.*", line) is not None:
                key, value = line.split("=", 1)
                existing_vars.append(key)

        missing_vars = []
        missing_default_vars = []
        for key, value in env_variables.items():
            has_default = value.get("default") is not None
            if has_default is True and (f"# {key}" not in existing_vars and key not in existing_vars):
                missing_default_vars.append(key)
            elif has_default is False and key not in existing_vars:
                missing_vars.append(key)

        if missing_vars:
            self.stdout.write(self.style.WARNING("Environment variables Missing in .env file:"))
            for var in missing_vars:
                self.stdout.write(f"- {var}")

        if missing_default_vars:
            self.stdout.write(self.style.WARNING("Environment variables Missing in .env file with default values:"))
            for var in missing_default_vars:
                self.stdout.write(f"- {var}")

        if not missing_vars and not missing_default_vars:
            self.stdout.write(self.style.SUCCESS("All environment variables are set."))

        orphaned_vars = [key for key in existing_vars if key.replace("# ", "") not in env_variables]
        if orphaned_vars:
            self.stdout.write(
                self.style.WARNING("\nEnvironment variables in .env file that are not defined in your Django settings:")
            )
            for var in orphaned_vars:
                self.stdout.write(f"- {var.replace('# ', '')}")
