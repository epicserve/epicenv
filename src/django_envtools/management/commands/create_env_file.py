from pathlib import Path

from django.core.management import BaseCommand
from django.utils import timezone

from django_envtools import get_dot_env_file_str


class Command(BaseCommand):
    help = "Either print or write to a file the initial .env file"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            nargs="?",
            default=None,
            help="Optional path to write the .env file. If not provided, the file will be created in the current "
            "working directory.",
        )

    def handle(self, *args, **options):
        path = options["path"]
        cwd = Path.cwd()
        if path is None:
            path = cwd / ".env"

        dot_env_file_str = get_dot_env_file_str()
        env_rel_path_str = path.relative_to(cwd)
        if path.exists() is True:
            # move file to a backup file
            now = timezone.now()
            new_file_path = path.with_name(f".env.{now.strftime('%Y%m%d%H%M%S')}")
            path.rename(new_file_path)

            new_file_path_rel_str = new_file_path.relative_to(cwd)
            self.stderr.write(
                self.style.WARNING(
                    f"File {env_rel_path_str} already exists and was backed up to {new_file_path_rel_str}.\n"
                )
            )

        path.write_text(dot_env_file_str)

        self.stdout.write(self.style.SUCCESS(f"{env_rel_path_str} file created."))
