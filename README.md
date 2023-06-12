# Fansly Stream Recorder

This script allows you to record fansly streams live to a .mp4 file and automatically upload the VOD to the cloud using rclone, and uses discord webhooks to keep you updated on the status(stream start/file conversion/upload).

⚠ This only works on public streams that don't require following/subs.

# Setting up


1. Install required python modules for the script:

   ```
   pip install -r requirements.txt
   ```

   Alongside installing [mt](https://github.com/mutschler/mt#installation-from-source) to genereate a contact-sheet of the live.
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

3. Replace instances of `webhook_url` to your webhook url for your notify channel, as well as replacing the id in `mention` for the role or user id to ping.  

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

Alternatively, you can use the `start.sh` script to create the tmux instances and run the script:

```
bash start.sh {username}
``` 

[more on tmux](https://www.hamvocke.com/blog/a-quick-and-easy-guide-to-tmux/)


# Super Serious Needed Disclaimer

> "Fansly" is operated by Select Media LLC 👺.
>
> This repository and the provided content in it isn't in any way affiliated with, sponsored by, or endorsed by Select Media LLC or "Fansly" 👺.
>
> The developer of this script is not responsible for the end users' actions 👺.
