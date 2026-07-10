### Adding a user to a private Discord thread

When Rodolfo asks to add Raquel or another user to a Zeus/Atena thread, use Discord API `PUT /channels/{thread_id}/thread-members/{user_id}`. Do this even when no dedicated `discord_admin` tool is loaded: load the bot token from the active profile `.env` inside a terminal/shell command, call Discord API directly, and never print the token. If it returns `403 Missing Access`, the likely cause is that the user is not in the parent channel yet; report that clearly, then retry the same PUT after Rodolfo grants parent-channel access. Do not claim the thread add succeeded until the API returns `204`.


