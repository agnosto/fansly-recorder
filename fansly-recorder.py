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

import config

rcloneConfig = """
[remote]
type = REPLACE
scope = ALL
token = THIS
"""
rcloneRemotePath = "remote:FanslyVODS/"

checkTimeout = (2 * 65)

async def getAccountData(account_url):
    resolver = aiohttp.resolver.AsyncResolver(
            nameservers=["8.8.8.8", "8.8.8.4", "1.1.1.1", "1.0.0.2"]
    )
    connector = aiohttp.TCPConnector(resolver=resolver)    
    async with aiohttp.ClientSession(connector=connector, headers=config.headers) as session:
        async with session.get(account_url) as response:
            json_data = await response.json()
            if not json_data["success"] or len(json_data["response"]) == 0:
                print("Error: could not retrieve account data")
                exit()
            #account_id = json_data['response'][0]['id']
            #return account_id            
            metadata = {
                "success": json_data["success"],
                "response": [
                    {
                        "id": json_data["response"][0]["id"],
                        "username": json_data["response"][0]["username"],
                        "avatar": {
                            "id": json_data["response"][0]["avatar"]["id"],
                            "mimetype": json_data["response"][0]["avatar"]["mimetype"],
                            "location": json_data["response"][0]["avatar"]["location"],
                            "variants": [
                                {
                                    "id": json_data["response"][0]["avatar"][
                                        "variants"
                                    ][0].get("id", None),
                                    "mimetype": json_data["response"][0]["avatar"][
                                        "variants"
                                    ][0].get("mimetype", None),
                                    "location": json_data["response"][0]["avatar"][
                                        "variants"
                                    ][0].get("location", None),
                                    "locations": [
                                        {
                                            "locationId": json_data["response"][0][
                                                "avatar"
                                            ]["variants"][0]["locations"][0].get(
                                                "locationId", None
                                            ),
                                            "location": json_data["response"][0][
                                                "avatar"
                                            ]["variants"][0]["locations"][0].get(
                                                "location", None
                                            ),
                                        }
                                    ],
                                },
                            ],
                        },
                    }
                ],
            }


    return metadata

async def getStreamData(stream_url):
    resolver = aiohttp.resolver.AsyncResolver(
            nameservers=["8.8.8.8", "8.8.8.4", "1.1.1.1", "1.0.0.2"]
    )
    connector = aiohttp.TCPConnector(resolver=resolver)
    async with aiohttp.ClientSession(connector=connector, headers=config.headers) as session:
        async with session.get(stream_url) as response:
            data = await response.json()

    last_fetched = data["response"]["stream"]["lastFetchedAt"]
    current_time = int(datetime.now().timestamp() * 1000)
    access = (data["response"]["stream"]["access"],)

    if current_time - last_fetched > 2 * 60 * 1000 or not access:
        return {"success": False, "response": None}
    else:
        metadata = {
            "success": data["success"],
            "response": {
                "id": data["response"]["id"],
                "accountId": data["response"]["accountId"],
                "playbackUrl": data["response"]["playbackUrl"],
                "createdAt": data["response"]["createdAt"],
                "stream": {
                    "id": data["response"]["stream"]["id"],
                    "title": data["response"]["stream"]["title"],
                    "status": data["response"]["stream"]["status"],
                    "viewerCount": data["response"]["stream"]["viewerCount"],
                    "version": data["response"]["stream"]["version"],
                    "createdAt": data["response"]["stream"]["createdAt"],
                    "lastFetchedAt": data["response"]["stream"]["lastFetchedAt"],
                    "startedAt": data["response"]["stream"]["startedAt"],
                    "access": data["response"]["stream"]["access"],
                    "playbackUrl": data["response"]["stream"].get("playbackUrl", None),
                },
            },
        }
    #print(metadata)
    return metadata

async def ffmpegSync(filename, data, user_Data):
    directory = os.path.join("./captures", user_Data["response"][0]["username"])
    os.makedirs(directory, exist_ok=True)
    ts_filename = os.path.join(directory, f"{filename}.ts")
    print(f"[ffmpeg] Saving livestream to {ts_filename}")
    
    command = f'ffmpeg -i {data["response"]["stream"]["playbackUrl"]} -c copy -movflags use_metadata_tags -map_metadata 0 -timeout 300 -reconnect 300 -reconnect_at_eof 300 -reconnect_streamed 300 -reconnect_delay_max 300 -rtmp_live live {ts_filename}'
    subprocess.run(command, shell=True, check=True)
    
    print(f"[ffmpeg] Done saving livestream to {filename}.ts")
    return ts_filename

async def convertToMP4(ts_filename):
    mp4_filename = ts_filename.rsplit('.', 1)[0] + '.mp4'
    #ts_filename = f"{filename}.ts"
    #mp4_filename = f"{filename}.mp4"

    if config.ffmpeg_convert == True:
        (
            ffmpeg
            .input(ts_filename, re=None)
            .output(mp4_filename, vcodec='copy', acodec='copy')
            .global_args('-loglevel', 'quiet')
            .run()
        )
    else:
        os.rename(ts_filename, mp4_filename)

    if config.webhooks.enabled == True:

        # Send Discord notification that conversion is complete
        webhook_url = config.webhooks.info_webhook
        if webhook_url is not None:
            webhook = DiscordWebhook(url=webhook_url)
        # Set message content
            mp4_name = os.path.basename(mp4_filename)
            webhook.content = f"Converted {ts_filename} to {mp4_name}"
            response = webhook.execute()
            if response.status_code == 200:
                print(f"[info] Sent Discord notification that {ts_filename} was converted to {mp4_name}")
            else:
                print(
                    f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}"
                )
        return mp4_filename
    else:
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

async def uploadRecording(mp4_filename, contact_sheet_filename):
    
    if config.webhooks.enabled == True:
        # Send Discord notification that upload is complete
        webhook_url = config.webhooks.info_webhook  
        if webhook_url is not None:
            webhook = DiscordWebhook(url=webhook_url)
            mp4_name = os.path.basename(mp4_filename)
            sheet_name = os.path.basename(contact_sheet_filename)
            mention = config.webhooks.webhook_mention 
        
            # Create DiscordEmbed object
            embed = DiscordEmbed(title="Stream Recording Uploaded", description=f'Uploaded {mp4_name} with contact sheet {sheet_name}', color="03b2f8")
            embed.set_image(url=f"attachment://{sheet_name}")
            embed.set_timestamp()
        
            # Add message and embed to webhook
            webhook.content = f"{mention} Vod Uploaded"
            webhook.add_file(file=open(contact_sheet_filename, "rb"), filename=sheet_name)
            webhook.add_embed(embed)

            # Send webhook message
            response = webhook.execute()
            if response.status_code == 200:
                print(f"[info] Sent Discord notification that {mp4_name} was uploaded")
            else:
                print(
                    f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}"
                )
    
    if config.mt == True:
        rclone.with_config(rcloneConfig).run_cmd(command="move", extra_args=[contact_sheet_filename, rcloneRemotePath])
    rclone.with_config(rcloneConfig).run_cmd(command="move", extra_args=[mp4_filename, rcloneRemotePath])

async def startRecording(user_Data, data):
    global checkTimeout
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_Data['response'][0]['username']}_{current_datetime}_v{data['response']['stream']['id']}"
    
    ts_filename = await ffmpegSync(filename, data, user_Data)

    # Convert .ts file to .mp4
    mp4_filename = await convertToMP4(ts_filename)

    if config.mt:
        contact_sheet_filename = await generateContactSheet(mp4_filename)

    if config.upload is True and config.mt is True:
        await uploadRecording(mp4_filename, contact_sheet_filename)
    elif config.upload is True:
        await uploadRecording(mp4_filename)

    if config.ffmpeg_convert is True:
        # Delete the .ts file
        #ts_filename = f"{filename}.ts"
        os.remove(ts_filename)

    print(f"[info] Stream complete. Resuming online check")
    await asyncio.sleep(checkTimeout)

async def sendWebhookLive(user_Data):
    webhook_url_startstream = config.webhooks.live_webhook 
    webhook = DiscordWebhook(url=webhook_url_startstream)

    live_url = f"https://fansly.com/live/{user_Data['response'][0]['username']}"
    mention = config.webhooks.webhook_mention
    content = f"{mention} {user_Data['response'][0]['username']} is now live on Fansly!"
    embed_live = DiscordEmbed(title='Stream Live!', color='03b2f8', url=live_url,)
    embed_live.set_author(
        name=f"{user_Data['response'][0]['username']}", 
        icon_url=f"{user_Data['response'][0]['avatar']['variants'][0]['locations'][0]['location']}"
    )
    embed_live.set_thumbnail(
        url=f"{user_Data['response'][0]['avatar']['variants'][0]['locations'][0]['location']}"
    )
    embed_live.set_timestamp()
    webhook.add_embed(embed_live)
    webhook.content = content

    response = webhook.execute()
    if response.status_code == 200:
        print(
            f"[info] {user_Data['response'][0]['username']} Stream is online, starting archiver"
        )
    else:
        print(
            f"[warning] Failed to send webhook notification: {response.status_code} {response.reason}"
        )

async def Start():
    if len(sys.argv) < 2:
        print("[Error] Usage: python fansly-recorder.py <username>")
        return

    username = sys.argv[1]   
    account_url = (
        f"https://apiv3.fansly.com/api/v1/account?usernames={username}&ngsw-bypass=true"
    )

    user_Data = await getAccountData(account_url)
    account_id = user_Data["response"][0]["id"]
    
    stream_url = f"https://apiv3.fansly.com/api/v1/streaming/channel/{account_id}?ngsw-bypass=true"
    print(f"[info] Starting online check for {user_Data['response'][0]['username']}")

    while True:
        data = await getStreamData(stream_url)

        if (
            data is not None 
            and data["success"] 
            and data["response"]["stream"]["access"]
        ):
            if config.webhooks.enabled == True:
                await sendWebhookLive(user_Data)
                await startRecording(user_Data, data)
            else:
                print(
                    f"[info] {user_Data['response'][0]['username']} Stream is online, starting archiver"
                )
                await startRecording(user_Data, data)
        else:
            print(
                f"[info] {user_Data['response'][0]['username']} is offline, checking again in {checkTimeout}s"
            )
            await asyncio.sleep(checkTimeout)

asyncio.run(Start())
