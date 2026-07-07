Log out and back in so your new group membership takes effect. Then run Codex as the dedicated user:

```bash
sudo -iu codex
```

Group rules:

- Keep `codex` as the account's private primary group.
- Add it only to `codex-work`.
- Do not add it to `sudo`, `docker`, `lxd`, `disk`, `shadow`, or `adm`. Several of these provide root-equivalent or sensitive access.
- Use mode `2770` on shared workspace directories:
  - Owner and group: full access.
  - Others: no access.
  - Setgid bit: new files inherit `codex-work`.
- Use `umask 0007` for both users when working there, ensuring group-write access without exposing files to other users.
- Give access only to selected repositories, not your entire home directory.
- Groups do not restrict network access; Codex sandbox settings, firewall rules, or containers handle that separately.

Check the account:

```bash
id codex
sudo -u codex test -w /srv/codex-workspaces
sudo -l -U codex
```

The final command should show that `codex` has no sudo privileges. Its global Codex guidance belongs at `/home/codex/.codex/AGENTS.md`.

Assumption: selected projects currently means `/home/blaine/wizytki_jaslo_page`. Do not expose all of `/home/blaine`.

After creating `codex` and `codex-work`, configure both locations:

```bash
# Shared workspace
sudo install -d -o "$USER" -g codex-work -m 2770 /srv/codex-workspaces

# Permit traversal of your home, without permitting directory listing
sudo setfacl -m u:codex:--x /home/blaine

# Share the selected existing project
sudo chgrp -R codex-work /home/blaine/wizytki_jaslo_page
sudo chmod -R g+rwX /home/blaine/wizytki_jaslo_page
sudo find /home/blaine/wizytki_jaslo_page -type d -exec chmod g+s {} +
```

Add default ACLs so future files remain group-accessible:

```bash
sudo find /home/blaine/wizytki_jaslo_page -type d \
  -exec setfacl -m g:codex-work:rwx,d:g:codex-work:rwx,d:m:rwx {} +

sudo setfacl -m g:codex-work:rwx,d:g:codex-work:rwx,d:m:rwx \
  /srv/codex-workspaces
```

Verify:

```bash
sudo -u codex test -r /home/blaine/wizytki_jaslo_page
sudo -u codex test -w /home/blaine/wizytki_jaslo_page
sudo -u codex test -w /srv/codex-workspaces
namei -l /home/blaine/wizytki_jaslo_page
```

If `setfacl` is unavailable:

```bash
sudo apt install acl
```

Security note: access to the project includes its `.git` directory and any secrets stored inside it. Remove secrets or restrict them separately before granting access.
