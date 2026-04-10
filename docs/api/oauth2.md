# OAuth2

OAuth2 lets users log in to your website or app with their Nerimity account — similar to "Login with Discord/Google".

## Setup

1. Go to [nerimity.com/app/settings/developer/applications](https://nerimity.com/app/settings/developer/applications)
2. Open your application → **OAuth2** tab
3. Add your redirect URI (e.g. `http://localhost:8000/callback`)
4. Copy your **Client ID** and **Client Secret**

## Quickstart

```python
from nerimity_sdk import OAuth2Client

client = OAuth2Client(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_uri="http://localhost:8000/callback",
)
```

## Authorization flow

### 1. Redirect the user to Nerimity

```python
url = client.authorization_url(scopes=["identify"])
# Send the user to this URL
print(url)
```

### 2. Exchange the code for a token

When Nerimity redirects back to your app it includes a `code` query parameter:

```python
token = await client.exchange_code(code="CODE_FROM_QUERY_PARAM")
```

### 3. Fetch the user

```python
user = await client.fetch_user(token.access_token)
print(user.username, user.id)
```

## Refresh a token

Access tokens expire. Use the refresh token to get a new one without making the user log in again:

```python
new_token = await client.refresh_token(token.refresh_token)
```

## Scopes

| Scope | What it grants |
|---|---|
| `identify` | Read the user's username, tag, and avatar |
| `servers` | List the servers the user is in |

## Full example with aiohttp

```python
from aiohttp import web
from nerimity_sdk import OAuth2Client

client = OAuth2Client(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    redirect_uri="http://localhost:8000/callback",
)

async def login(request):
    raise web.HTTPFound(client.authorization_url(scopes=["identify"]))

async def callback(request):
    code = request.rel_url.query["code"]
    token = await client.exchange_code(code)
    user = await client.fetch_user(token.access_token)
    return web.Response(text=f"Logged in as {user.username}!")

app = web.Application()
app.router.add_get("/login", login)
app.router.add_get("/callback", callback)
web.run_app(app, port=8000)
```
