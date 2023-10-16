import os
from github import Github, GithubException
from fire import Fire
from yaml import load
from datetime import datetime

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

def main(cfg: str):
    CONFIG = load(open(cfg, 'r'), Loader=Loader)
    github_token = CONFIG['github_token']
    repo_name = CONFIG['repo_name']
    system_id = CONFIG['id']
    g = Github(github_token)
    repo = g.get_user().get_repo(repo_name)

    # Create a "logs" folder if it doesn't exist in the repository
    logs_folder_name = 'logs'
    #if not any(x.path == logs_folder_name for x in repo.get_contents('')):
     #   repo.create_file(logs_folder_name, "Create logs folder", "", branch="main")
    
    file_name = f'{logs_folder_name}/{system_id}.log'

    # Query GPU utilization using nvidia-smi
    nvidia_smi_output = os.popen('nvidia-smi --query-gpu=index,utilization.gpu --format=csv,noheader,nounits').readlines()

    # Get the number of GPUs
    num_gpus = len(nvidia_smi_output)

    # Format and write the utilization data to the log
    log_content = []
    for line in nvidia_smi_output:
        gpu_id, utilization = line.strip().split(',')
        log_content.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{gpu_id}\t{utilization}")

    # Join the log lines into a single string
    log_text = "\n".join(log_content)

    # Read the existing log file if it exists
    try:
        content = repo.get_contents(file_name, ref="main")
        existing_log = content.decoded_content.decode('utf-8')
    except GithubException as e:
        # Handle the case where the file doesn't exist
        if e.status == 404:
            existing_log = ""
            # Create an empty file
            repo.create_file(file_name, "Initial Commit", "", branch="main")
        else:
            # Handle other GitHub exceptions
            print(f"GitHub Error: {e}")
            existing_log = ""

    # Calculate the maximum number of lines based on the number of GPUs
    max_lines = 10000 * num_gpus

    # Append the new log content
    updated_log = existing_log + "\n" + log_text

    # Check the line count and move old lines to a separate file if needed
    if updated_log.count('\n') > max_lines:
        old_log_name = f'{logs_folder_name}/{system_id}.old'
        old_log_content = updated_log.split('\n', 1)[1]  # Remove the first line to keep the count below the maximum
        repo.create_file(old_log_name, f"Old GPU Stats - System {system_id}", old_log_content, branch="main")
        updated_log = log_text

    # Update the log file in the repository
    repo.update_file(file_name, f"Updated GPU Stats - System {system_id}", updated_log, content.sha, branch="main")

    print(f"System {system_id} GPU utilization stats pushed to GitHub. Max lines allowed: {max_lines}")

if __name__ == '__main__':
    Fire(main)