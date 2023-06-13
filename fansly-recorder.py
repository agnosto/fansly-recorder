import aiohttp
import asyncio
from datetime import datetime
import ffmpeg
import sys
import rclone 
import os
import subprocess

from os.path import expanduser

from discord_webhook import DiscordWebhook, DiscordEmbed

rcloneConfig = """
[remote]
type = REPLACE
scope = ALL
token = THIS
"""
rcloneRemotePath = "remote:FanslyVODS/"

checkTimeout = (5 * 60)
headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

async def getAccountData(account_url):
    resolver = aiohttp.resolver.AsyncResolver(nameservers=['8.8.8.8'])
    connector = aiohttp.TCPConnector(resolver=resolver)    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        async with session.get(account_url) as response:
            json_data = await response.json()
            if not json_data['success'] or len(json_data['response']) == 0:
                print('Error: could not retrieve account data')
                exit()
            #account_id = json_data['response'][0]['id']
    #return account_id            
            metadata = {
              "success": json_data['success'],
              "response": [
                  {
                      "id": json_data['response'][0]['id'],
                      "username": json_data['response'][0]['username'],
                      "avatar": {
                        "id": json_data['response'][0]['avatar']['id'],
                        "mimetype": json_data['response'][0]['avatar']['mimetype'],
                        "location": json_data['response'][0]['avatar']['location'],
                        "variants": [
                            {
                            "id": json_data['response'][0]['avatar']['variants'][0]['id'],
                            "mimetype": json_data['response'][0]['avatar']['variants'][0]['mimetype'],
                            "location": json_data['response'][0]['avatar']['variants'][0]['location'],
                            "locations": [{
                                "locationId": json_data['response'][0]['avatar']['variants'][0]['locations'][0]['locationId'],
                                "location": json_data['response'][0]['avatar']['variants'][0]['locations'][0]['location'],
                            }]
                      }
                        ]
                      }
                  }
              ]
          }

    return metadata

async def getStreamData(stream_url):
    resolver = aiohttp.resolver.AsyncResolver(nameservers=['8.8.8.8'])
    connector = aiohttp.TCPConnector(resolver=resolver)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        async with session.get(stream_url) as response:
            data = await response.json()

    last_fetched = data['response']['stream']['lastFetchedAt']
    current_time = int(datetime.now().timestamp() * 1000)

    if current_time - last_fetched > 4 * 60 * 1000:
        return None
    else:

        metadata = {
          "success": data['success'],
          "response": {
              "id": data['response']['id'],
              "accountId": data['response']['accountId'],
              "playbackUrl": data['response']['playbackUrl'],
              "stream": {
                  "id": data['response']['stream']['id'],
                  "title": data['response']['stream']['title'],
                  "status": data['response']['stream']['status'],
                  "lastFetchedAt": data['response']['stream']['lastFetchedAt'],
                  "startedAt": data['response']['stream']['startedAt'],
                  "playbackUrl": data['response']['stream']['playbackUrl']
              },
          }
      }
    #print(metadata)
    return metadata

async def ffmpegSync(filename, data):
    print(f"[ffmpeg] Saving livestream to {filename}.ts")
    
    (
        ffmpeg
        .input(data["response"]["stream"]["playbackUrl"], re=None)
        .output(f'{filename}.ts', c='copy')
        .global_args('-loglevel', 'quiet')
        .run()
    )
    
    print(f"[ffmpeg] Done saving livestream to {filename}.ts")

async def convertToMP4(filename):
    ts_filename = f"{filename}.ts"
    mp4_filename = f"{filename}.mp4"
    (
        ffmpeg
        .input(ts_filename, re=None)
        .output(mp4_filename, vcodec='copy', acodec='copy')
        .global_args('-loglevel', 'quiet')
        .run()
    )

    # Send Discord notification that conversion is complete
    webhook_url = "https://discord.com/api/webhooks/1234567890/abcde"  # Replace with your webhook URL
    if webhook_url is not None:
        webhook = DiscordWebhook(url=webhook_url)
        # Set message content
        mp4_name = os.path.basename(mp4_filename)
        webhook.content = f"Converted {filename}.ts to {mp4_name}"
        response = webhook.execute()
        if response.status_code == 200:
            print(f"[info] Sent Discord notification that {filename}.ts was converted to {mp4_name}")
        else:
            print(f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}")

    return mp4_filename

async def generateContactSheet(mp4_filename):
    contact_sheet_filename = f"{os.path.splitext(mp4_filename)[0]}.jpg"
    subprocess.run([
        "./mt",
        "--columns=4",
        "--numcaps=24",
        "--header-meta",
        "--fast",
        "--comment=Archive - Fansly VODs",
        f"--output={contact_sheet_filename}",
        mp4_filename
    ])
    return contact_sheet_filename

async def uploadRecording(mp4_filename):
    contact_sheet_filename = await generateContactSheet(mp4_filename)

    with open(expanduser('~/.config/rclone/rclone.conf')) as config_file:
        config = config_file.read()
    #with rclone.with_config(rcloneConfig) as cfg:
        fs = rclone.with_config(config).new_fs("remote")
        fs.move(mp4_filename, rcloneRemotePath, verbose=True)
        fs.move(contact_sheet_filename, rcloneRemotePath, verbose=True)

    # Send Discord notification that upload is complete
    webhook_url = "https://discord.com/api/webhooks/1234567890/abcde"  # Replace with your webhook URL
    if webhook_url is not None:
        webhook = DiscordWebhook(url=webhook_url)
        mp4_name = os.path.basename(mp4_filename)
        sheet_name = os.path.basename(contact_sheet_filename)
        
        # Create DiscordEmbed object
        embed = DiscordEmbed(title='Stream Recording Uploaded', color='03b2f8')
        embed.set_image(url=f"attachment://{sheet_name}")
        
        # Add message and embed to webhook
        webhook.content = f"Uploaded {mp4_name} with contact sheet {sheet_name}"
        webhook.add_file(file=open(contact_sheet_filename, 'rb'), filename=sheet_name)
        webhook.add_embed(embed)

        # Send webhook message
        response = webhook.execute()
        if response.status_code == 200:
            print(f"[info] Sent Discord notification that {mp4_name} was uploaded")
        else:
            print(f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}")


async def startRecording(user_Data, data):
    global checkTimeout
    started_at_datetime = datetime.fromtimestamp(data["response"]["stream"]["startedAt"] / 1000)
    filename = f"{user_Data['response'][0]['username']}_{started_at_datetime.strftime('%Y%m%d_%H%M%S')}_v{data['response']['stream']['id']}"
    
    await ffmpegSync(filename, data)

    # Convert .ts file to .mp4
    mp4_filename = await convertToMP4(filename)
    await uploadRecording(mp4_filename)

    # Delete the .ts file
    ts_filename = f"{filename}.ts"
    os.remove(ts_filename)

    print(f"[info] Stream complete. Resuming online check")
    await asyncio.sleep(checkTimeout)

async def sendWebhookLive(user_Data):
    webhook_url_startstream = "https://discord.com/api/webhooks/1234567890/abcde"  # Replace with your start stream webhook URL
    webhook = DiscordWebhook(url=webhook_url_startstream)

    live_url = f"https://fansly.com/live/{user_Data['response'][0]['username']}"
    mention = "<@!123456789>"  # Replace with the user or role ID you want to mention (@! for user id,@& for role )
    content = f"{mention} {user_Data['response'][0]['username']} is now live on Fansly!"
    embed_live = DiscordEmbed(title='Stream Live!', color='03b2f8', url=live_url,)
    embed_live.set_author(name=f"{user_Data['response'][0]['username']}", icon_url=f"{user_Data['response'][0]['avatar']['variants'][0]['locations'][0]['location']}")
    embed_live.set_thumbnail(url=f"{user_Data['response'][0]['avatar']['variants'][0]['locations'][0]['location']}")
    embed_live.set_timestamp()
    webhook.add_embed(embed_live)
    webhook.content = content

    response = webhook.execute()
    if response.status_code == 200:
        print(f"[info] {user_Data['response'][0]['username']} Stream is online, starting archiver")
    else:
        print(f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}")

async def Start():
    if len(sys.argv) < 2:
        print("[Error] Usage: python fansly-recorder.py <username>")
        return

    username = sys.argv[1]   
    account_url = f'https://apiv3.fansly.com/api/v1/account?usernames={username}&ngsw-bypass=true'

    user_Data = await getAccountData(account_url)
    account_id = user_Data['response'][0]['id']
    
    stream_url = f'https://apiv3.fansly.com/api/v1/streaming/channel/{account_id}?ngsw-bypass=true'
    print(f"[info] Starting online check for {user_Data['response'][0]['username']}")

    while True:
        data = await getStreamData(stream_url)

        if data is not None and data['success']:
            await sendWebhookLive(user_Data)
            #print(f"[info] {user_Data['response'][0]['username']} Stream is online, starting archiver")
            await startRecording(user_Data, data)
        else:
            print(f"[info] {user_Data['response'][0]['username']} is offline, checking again in {checkTimeout}s")
            await asyncio.sleep(checkTimeout)

asyncio.run(Start())
