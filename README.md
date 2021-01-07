# saweria.py

Python API Wrapper for [Saweria.co](https://saweria.co/)

Checkout the [Node.js version](https://github.com/SuspiciousLookingOwl/saweria-api)

## Example

```py
import saweria

client = saweria.Client()


@client.event
async def on_donations(donation):
    print(donation[0])


@client.event
async def on_login(user):
    print(user)

    print(await client.get_available_balance())
    print(await client.get_milestone_progress("31-12-2020"))
    print(await client.get_balance())
    print(await client.get_leaderboard())
    print(await client.get_transactions())
    print(await client.get_user())



client.run("email", "password", otp="otp")
```