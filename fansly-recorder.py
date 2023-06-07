import aiohttp
import asyncio
from datetime import datetime
import ffmpeg
import sys
import rclone 

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

resolver = aiohttp.resolver.AsyncResolver(nameservers=['8.8.8.8'])
connector = aiohttp.TCPConnector(resolver=resolver)

async def getAccountData(account_url):    
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
                  }
              ]
          }

    return metadata

async def getStreamData(stream_url):
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

async def startRecording(user_Data, data):
    global checkTimeout
    started_at_datetime = datetime.fromtimestamp(data["response"]["stream"]["startedAt"] / 1000)
    filename = f"{user_Data['response'][0]['username']}_{started_at_datetime.strftime('%Y%m%d_%H%M%S')}_v{data['response']['stream']['id']}"
    
    await ffmpegSync(filename, data)

    with rclone.with_config(rcloneConfig) as cfg:
        fs = rclone.with_config(cfg).new_fs("remote")
        fs.move(f"{filename}.ts", rcloneRemotePath, verbose=True)

    print(f"[info] Stream complete. Resuming online check")
    await asyncio.sleep(checkTimeout)

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
            print(f"[info] {user_Data['response'][0]['username']} Stream is online, starting archiver")
            await startRecording(user_Data, data)
            break
        else:
            print(f"[info] {user_Data['response'][0]['username']} is offline, checking again in {checkTimeout}s")
            await asyncio.sleep(checkTimeout)

asyncio.run(Start())
