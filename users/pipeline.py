def set_github_username(backend, user, response, *args, **kwargs):
    if backend.name == "github":
        github_username = response.get("login", "")
        if github_username and user.github_username != github_username:
            user.github_username = github_username
            user.save(update_fields=["github_username"])
