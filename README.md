# Fansly Stream Recorder

This script allows you to record fansly streams live to a .ts file and automatically upload the VOD to the cloud using rclone.

⚠ Unsure if streams can be done behind a sub and not sure how this will handle that if possible.

(may add converting .ts files to .mp4 prior to pushing to remote)

# Setting up


1. Install required python modules for the script:
```
pip install - r requirements.txt
```
2. Install and create a rclone remote (`rclone config`) if you don't already have one and then edit `fansly-recorder.py` and add the following:

   - The rclone config `cat $HOME/.config/rclone/rclone.conf` for the host you want to push the files to
   - The remote path to `rcloneRemotePath`

Example:

```
rcloneConfig = """
[remote]
type = drive
scope = drive
token = {"access_token":"......."...}
"""
rcloneRemotePath = "remote:path/to/FanslyVods/"
```

# Running

The script will continue to loop and check for the model to be live and then start to record, once finished it will push the file to the remote and go back to checking for the model to be live again.


Run the script

```
python fansly-recorder.py {username}
```

Recommend to run the script in tmux to be able to close the terminal.

Create a new tmux session:

```
tmux new -s Fansly
```

Again run the script:

```
python fansly-recorder.py {username}
```

press `ctrl + b` then `d` to detach from the session.

[more on tmux](https://www.hamvocke.com/blog/a-quick-and-easy-guide-to-tmux/)


# Super Serious Needed Disclaimer

> "Fansly" is operated by Select Media LLC 👺.
>
> This repository and the provided content in it isn't in any way affiliated with, sponsored by, or endorsed by Select Media LLC or "Fansly" 👺.
>
> The developer of this script is not responsible for the end users' actions 👺.
