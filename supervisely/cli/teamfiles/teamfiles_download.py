import os
import supervisely as sly
import re

from tqdm import tqdm

import traceback
from rich.console import Console


def download_directory_run(
    team_id: int,
    remote_dir: str,
    local_dir: str,
    filter: str = None,
    ignore_if_not_exists: bool = False,
) -> bool:
    api = sly.Api.from_env()
    console = Console()

    if api.team.get_info_by_id(team_id) is None:
        console.print(
            f"\nError: Team with ID={team_id} is either not exist or not found in your acocunt\n",
            style="bold red",
        )
        return False

    # force directories to end with slash '/'
    if not local_dir.endswith("/"):
        local_dir += "/"
    if not remote_dir.endswith("/"):
        remote_dir += "/"

    files = api.file.listdir(team_id, remote_dir, recursive=True)
    if len(files) == 0:
        if ignore_if_not_exists:
            console.print(
                f"\nWarning: Team files folder '{remote_dir}' not exists. Skipping command...\n",
                style="bold yellow",
            )
            return True
        console.print(f"\nError: Team files folder '{remote_dir}' not exists\n", style="bold red")
        return False

    if filter is not None:
        filtered = [f for f in files if bool(re.search(filter, sly.fs.get_file_name_with_ext(f)))]

    console.print(
        f"\nDownloading directory '{remote_dir}' from Team files ...\n",
        style="bold",
    )


    try:
        if filter is not None:
            with tqdm(desc="Downloading from Team files...", total=len(filtered)) as p:
                for remote_path in filtered:
                    local_save_path = os.path.join(
                        local_dir,
                        os.path.dirname(remote_path).strip("/"),
                        os.path.basename(remote_path),
                    )
                    api.file.download(
                        team_id,
                        remote_path,
                        local_save_path,
                    )
                    p.update(1)
        else:
            total_size = api.file.get_directory_size(team_id, remote_dir)
            p = tqdm(
                desc="Downloading from Team files...", total=total_size, unit="B", unit_scale=True
            )
            api.file.download_directory(team_id, remote_dir, local_dir, progress_cb=p)

        console.print(
            f"\nTeam files directory was sucessfully downloaded to the local path: '{local_dir}'.\n",
            style="bold green",
        )
        return True

    except:
        console.print("\nDownload failed\n", style="bold red")
        traceback.print_exc()
        return False
