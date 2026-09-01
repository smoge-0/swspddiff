# Deploy the speed race bot on Proxmox (Debian LXC)

The bot runs in a Docker container **inside** an LXC container. The LXC
container holds Docker + the bot files (`sw_data.db`, `mapping.json`, the
`speedrace_bot/` code) — the Docker image itself is just Python + the bot
code, and mounts the data files read-only (exactly as `docker-compose.yml`
does).

Commands with `#` are run on the **Proxmox host** (SSH or shell), commands
with `$` are run **inside the LXC container**, and `PS>` are run on your
**Windows PC** (PowerShell).

---

## 1. Create the LXC container

On the Proxmox host, make sure a Debian 12 template is downloaded:

```bash
# Proxmox host
pveam update
pveam available --section system | grep -i debian-12
# if empty, download one, e.g.:
pveam download local debian-12-standard_12.7-1_amd64.tar.zst
```

Create the container. **`nesting=1` is required for Docker** (and `keyctl=1`
for some runtimes). Replace `100` with a free CT ID and adjust disk/RAM:

```bash
# Proxmox host
pct create 100 local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname speedrace-bot \
  --memory 1024 \
  --cores 2 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1,keyctl=1 \
  --unprivileged 1 \
  --ostype debian \
  --onboot 1

pct start 100
pct enter 100
```

(`--onboot 1` starts the CT after a Proxmox reboot. To do this via the GUI
instead: Create CT → template `debian-12-standard` → Options → Features →
tick **Nesting** + **keyctl**.)

---

## 2. Install Docker inside the container

```bash
# inside LXC
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2
systemctl enable --now docker
docker --version && docker compose version
```

Both come from Debian's own repos — no curl-pipe-to-shell script needed.

---

## 3. Get the bot code into the container

The repo is self-contained: bot code + `mapping.json` are in the repo, and
`sw_data.db` is **auto-created on first run** (from the swarfarm API, into the
docker volume) — no data files to copy.

Clone the repo (recommended — makes updates a `git pull`):

```bash
# inside LXC
apt install -y git
git clone https://github.com/smoge-0/swspddiff.git /opt/swspddiff
```

Or copy from your PC if you don't want git on the container (PowerShell):

```powershell
# Windows PowerShell
scp -r speedrace_bot root@<CT-IP>:/opt/swspddiff
```

---

## 4. Configure the bot

```bash
# inside LXC
cd /opt/swspddiff
nano .env        # DISCORD_TOKEN=... and optionally GUILD_ID=...
chmod 600 .env
```

- `DISCORD_TOKEN` — required. (If you reset the token in the Developer
  Portal, update this file.)
- `GUILD_ID` — optional; set it to your server's ID for instant guild-scoped
  command sync instead of the up-to-1-hour global sync.

---

## 5. Build and start

```bash
# inside LXC
cd /opt/swspddiff
docker compose up -d --build
docker compose logs -f
```

You should see:

```
INFO:speedrace:logged in as swspddiff#3349
INFO:speedrace:synced 1 command(s)
```

On the first start the bot also logs creating `sw_data.db` from the swarfarm
API (needs outbound network once); afterwards the db + cache live in the
`speedrace-data` volume. The compose file sets `restart: unless-stopped`, so
the bot survives container restarts and Proxmox reboots automatically.

> **Before switching over:** the bot is currently running on your Windows PC.
> Discord only allows one active connection per token, so stop the Windows
> instance first (it will otherwise get disconnected when the LXC one
> connects).

---

## 6. Updating

| What changed | Do this |
|---|---|
| Bot code (`bot.py`, ...) | `git pull` in `/opt/swspddiff`, then `docker compose up -d --build` |
| `sw_data.db` / monster list | recreate from swarfarm: `docker compose exec speedrace-bot rm -f /app/speedrace_bot/data/sw_data.db` then `docker compose restart` |
| Token / `GUILD_ID` | edit `.env`, then `docker compose restart` |
| See logs / stop | `docker compose logs -f` / `docker compose down` (the `speedrace-data` volume is kept) |

---

## 7. Troubleshooting

- **Docker daemon fails with overlay/`operation not permitted` errors** — a
  known LXC quirk. Set the storage driver to `vfs`:
  ```bash
  # inside LXC
  mkdir -p /etc/docker
  echo '{"storage-driver":"vfs"}' > /etc/docker/daemon.json
  systemctl restart docker
  docker compose up -d --build
  ```
- **Unprivileged CT**: the bot writes only into the `speedrace-data` volume
  (owned by the container's uid 1000), so no host file permissions to manage.
- **Command doesn't appear in Discord**: check the bot is in the server and
  `GUILD_ID` is correct; without `GUILD_ID`, global sync can take up to an
  hour.
- **No outbound network**: the bot needs outbound HTTPS (443) to Discord and
  swarfarm (the latter only for the first-run `sw_data.db` bootstrap and the
  7-day refresh); no inbound ports are required. If the CT has a firewall,
  allow outbound 443.
- **`env file not found: .env`** on `docker compose up` — the `.env` file is
  missing in `/opt/swspddiff`; create it (step 4).
