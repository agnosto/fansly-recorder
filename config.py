mt = True
upload = True
webhooks = {
  'enabled': True,  # Set to True or False based on your requirement
  'live_webhook': 'webhook_url',  # Replace with the live webhook URL
  'info_webhook': 'webhook_url'  # Replace with the info webhook URL
}
headers = {
        'authority': 'apiv3.fansly.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en;q=0.8,en-US;q=0.7',
        'authorization': 'your_auth_token_here',  # Replace with your actual auth token
        'origin': 'https://fansly.com',
        'referer': 'https://fansly.com/',
        'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
}