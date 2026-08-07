# SecureOps Local — Runtime Readiness

Last verified: **2026-08-07**

This file records readiness evidence for the local runtimes used by SecureOps Local.
Installation, upgrade, model acquisition, model-cache population, and inference are
outside this prerequisite work.

## Inventory summary

| Runtime | Version | Verified endpoint | State |
|---|---|---|---|
| Docker Desktop | Desktop 4.85.0; Engine/CLI 29.6.2 | `npipe:////./pipe/dockerDesktopLinuxEngine` | Engine healthy; Windows `PATH` limitation |
| Ollama | CLI/API 0.32.6 | `http://127.0.0.1:11434/api` | Healthy; external model cache configured and empty |
| Foundry Local | CLI 0.10.2 | Dynamic `http://127.0.0.1:48077` for this run | Daemon ready; no model or execution-provider payloads cached |

Versions, endpoints, and state in this table are derived from the commands and exact
outputs in the runtime-specific sections below. No model response was requested or
verified.

## Docker Desktop and WSL 2

### Result

Docker Desktop and its Linux engine are healthy. Docker commands work through the
installed CLI executable and from the integrated Ubuntu WSL 2 distribution. The
current Windows process environment does not include `docker.exe` on `PATH`, so a
bare `docker` command fails in PowerShell.

### Version evidence

Command:

```powershell
(Get-Item 'C:\Users\husoelrey\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe').VersionInfo
```

Observed product and file version: `4.85.0.235549`.

Command:

```powershell
& 'C:\Users\husoelrey\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' version
```

Exit code: `0`.

Relevant output:

```text
Client: Docker CLI 29.6.2, API 1.55, windows/amd64
Server: Docker Desktop 4.85.0 (235549)
Engine: 29.6.2, API 1.55, linux/amd64
containerd: v2.2.5
runc: 1.3.6
```

### Context, endpoint, and engine health

Commands:

```powershell
& 'C:\Users\husoelrey\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' context show
& 'C:\Users\husoelrey\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' context inspect
& 'C:\Users\husoelrey\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' info --format 'ServerVersion={{.ServerVersion}} OSType={{.OSType}} Architecture={{.Architecture}} OperatingSystem={{.OperatingSystem}} CPUs={{.NCPU}} TotalMemory={{.MemTotal}}'
```

Each command exited `0`.

Observed state:

- Active context: `desktop-linux`
- Engine endpoint: `npipe:////./pipe/dockerDesktopLinuxEngine`
- TLS verification override: disabled
- Server version: `29.6.2`
- Server OS and architecture: `linux`, `x86_64`
- Server operating system: `Docker Desktop`
- Allocated CPUs: `18`
- Allocated memory: `8072753152` bytes
- Docker Desktop and `com.docker.backend` processes were running.

The successful server responses from `docker version` and `docker info` verify engine
health. No image was pulled and no container was created.

### WSL 2 and Docker integration

Commands:

```powershell
wsl --version
wsl --status
wsl --list --verbose
wsl -d Ubuntu -- docker version
```

Each command exited `0`.

Observed state:

- WSL version: `2.3.26.0`
- Kernel version: `5.15.167.4-1`
- Default distribution: `Ubuntu`
- Default WSL version: `2`
- `Ubuntu`: running as WSL 2
- `docker-desktop`: running as WSL 2
- Ubuntu Docker CLI: `29.6.2`, `linux/amd64`
- Ubuntu reached Docker Desktop server `4.85.0` and Engine `29.6.2`.

This proves that Docker Desktop's Ubuntu WSL integration is active. It does not yet
prove application-container access to host runtime endpoints through
`host.docker.internal`; that is a later P1 connectivity check.

### Failure and minimum reproduction

Command:

```powershell
docker version
```

Observed result: PowerShell raised `CommandNotFoundException` because `docker` was not
resolvable from the current Windows `PATH`. An external process was not started, so
there was no Docker process exit code.

Minimum reproduction:

```powershell
docker version
```

Fallback implication: use the verified absolute CLI path shown above or the integrated
Ubuntu WSL CLI until Windows `PATH` configuration is deliberately addressed. The
engine itself is healthy, so native Windows application fallback remains viable; CLI
path resolution is a developer-shell limitation rather than an engine failure.

## Ollama

### Result

Ollama CLI `0.32.6` is installed and available on the Windows `PATH`. Its local
process and loopback API are healthy. Its model cache is configured at the approved
external path and both that path and the old default contain no files. This work did
not list models through the API, acquire artifacts, or run inference.

The endpoint and cache interpretation follow the official
[Ollama API version endpoint](https://docs.ollama.com/api-reference/get-version) and
[Ollama for Windows](https://docs.ollama.com/windows) documentation checked on
2026-08-07.

### CLI version

Commands:

```powershell
Get-Command ollama
ollama --version
```

Both commands succeeded; `ollama --version` exited `0`.

Observed state:

- Executable: `C:\Users\husoelrey\AppData\Local\Programs\Ollama\ollama.exe`
- CLI version: `0.32.6`

### Process, endpoint, and API health

Commands:

```powershell
Get-Process -Name 'ollama','ollama app'
Get-NetTCPConnection -LocalPort 11434 -State Listen
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 5
```

Each check succeeded. The HTTP request returned a successful response, recorded as
exit code `0` by the inventory wrapper.

Observed state:

- `ollama.exe` process ID: `30072`
- `ollama app.exe` process ID: `11224`
- Listener: `127.0.0.1:11434`, owned by process `30072`
- Local API base URL: `http://127.0.0.1:11434/api`
- Version response: `{"version":"0.32.6"}`

The matching CLI and API versions plus the loopback listener verify local service
health. Process IDs are observations from this run and are expected to change after a
restart.

### External model-cache configuration

The current primary [Ollama FAQ](https://docs.ollama.com/faq) and
[Ollama for Windows](https://docs.ollama.com/windows) guidance checked on
2026-08-07 identifies the `OLLAMA_MODELS` environment variable as the supported way
to move model storage on Windows. It instructs users to quit the running application,
set the user environment variable, and relaunch Ollama.

Before the change, the old cache existed with only empty `blobs` and `manifests`
directories. The approved external root was empty, the `ollama` child did not exist,
and `OLLAMA_MODELS` was unset at process, user, and machine scopes.

Configuration commands:

```powershell
$newCache = 'C:\Users\husoelrey\Documents\docs\AI_models\ollama'
New-Item -ItemType Directory -Path $newCache
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $newCache, 'User')
[Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
```

The wrapper validated that the normalized child path remained below
`C:\Users\husoelrey\Documents\docs\AI_models` before creating it. Exit code: `0`.
The persistent user-scope value returned exactly:

```text
C:\Users\husoelrey\Documents\docs\AI_models\ollama
```

Only the installed Ollama processes were restarted. Their executable paths were
validated before stopping them:

```powershell
Stop-Process -Id 29060,3980
$env:OLLAMA_MODELS = [Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
Start-Process -FilePath 'C:\Users\husoelrey\AppData\Local\Programs\Ollama\ollama app.exe' -WindowStyle Hidden
```

Each command exited `0`. Explicitly copying the persisted value into the launch
environment ensures that the relaunched application and its `ollama.exe serve` child
received the same effective model path without depending on an existing desktop
process to refresh its environment block.

Post-restart evidence:

- `ollama app.exe`: PID `11224`, started
  `2026-08-07T12:15:04.5289748+03:00`
- `ollama.exe serve`: PID `30072`, started
  `2026-08-07T12:15:06.7363343+03:00`
- Listener: `127.0.0.1:11434`, owned by PID `30072`
- API response: `{"version":"0.32.6"}`
- Persisted and launch-environment model path:
  `C:\Users\husoelrey\Documents\docs\AI_models\ollama`

Verification commands:

```powershell
[Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
Get-ChildItem -LiteralPath 'C:\Users\husoelrey\.ollama\models' -Recurse -Force -File
Get-ChildItem -LiteralPath 'C:\Users\husoelrey\Documents\docs\AI_models\ollama' -Recurse -Force -File
Get-CimInstance Win32_Process -Filter "Name='ollama.exe' OR Name='ollama app.exe'"
Get-NetTCPConnection -LocalPort 11434 -State Listen
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 5
```

Observed state:

- Effective external cache exists: yes
- External cache files: `0`
- External cache bytes: `0`
- Old default cache files: `0`
- Old default cache bytes: `0`
- No existing artifact was moved or deleted
- No model-list, pull, create, import, or inference command was run

### Failure and fallback implications

No Ollama readiness command failed. The service binds only to Windows loopback in the
observed state, which is safe for local use but does not prove reachability from a
Docker container. `host.docker.internal:11434` connectivity and any required trusted
host-binding change remain a later, explicit P1 test. Native Windows FastAPI can use
the verified loopback endpoint if container-to-host access is unavailable.

## Microsoft Foundry Local

### Result

Foundry Local CLI `0.10.2` is installed and available on the Windows `PATH`. Its
daemon was deliberately started with the installed CLI and reached the CLI-reported
`ready` state. For this run it exposed the dynamic loopback endpoint
`http://127.0.0.1:48077` from process `foundrylocald` PID `23948`; both values are
ephemeral and must be discovered again after a restart.

The current primary reference checked on 2026-08-07 was Microsoft's
[Foundry Local CLI guidance](https://learn.microsoft.com/en-us/azure/foundry-local/how-to/how-to-use-foundry-local-cli).
That page describes `foundry service status` and warns that a first
`foundry model list` can download execution providers. The installed CLI behaves
differently: its built-in help exposes the daemon group as `foundry server` and
rejects `foundry service`. The installed `--help` output was therefore treated as
the executable contract. No model-list, model-download, load, or inference command
was run.

### CLI version and command surface

Commands:

```powershell
Get-Command foundry
foundry --version
foundry --help
foundry server --help
foundry cache --help
```

Each command exited `0`.

Observed state:

- Command shim: `C:\Users\husoelrey\AppData\Local\Microsoft\WindowsApps\foundry.exe`
- CLI version: `0.10.2`
- Installed daemon command group: `server`
- Read-only daemon check: `foundry server status`
- Read-only cache-location check: `foundry cache location`

### Daemon startup, health, and endpoint

Before startup, these commands established the baseline:

```powershell
foundry server status --output json
foundry cache location --output json
foundry config show --output json
Test-Path -LiteralPath 'C:\Users\husoelrey\.foundry\cache'
Test-Path -LiteralPath 'C:\Users\husoelrey\Documents\docs\AI_models'
# For each existing path:
Get-ChildItem -LiteralPath <path> -Recurse -Force -File
Get-ChildItem -LiteralPath <path> -Recurse -Force -Directory
```

Each CLI command exited `0`; both filesystem inspections completed successfully.
The exact status and cache-location outputs were:

```json
{"running":false,"state":"not_running"}
{"path":"C:\\Users\\husoelrey\\.foundry\\cache\\models","userSet":false}
```

The default Foundry cache did not exist. The approved external root existed and was
empty: `0` files, `0` bytes, and no child directories.

Startup command:

```powershell
foundry server start --output json
```

Exit code: `0`.

Exact output:

```json
{"running":true,"webUrls":["http://127.0.0.1:48077"],"port":48077}
```

Readiness command:

```powershell
foundry server status --output json
```

Exit code: `0`.

Exact output:

```json
{"running":true,"state":"ready","pid":23948,"webUrls":["http://127.0.0.1:48077"],"startedAt":"2026-08-07T09:08:14.8675625+00:00","uptime":"0s","logFile":""}
```

`Get-Process -Id 23948` resolved the reported PID to `foundrylocald`, with process
start time `2026-08-07T12:08:13.4033438+03:00`. A `TcpClient` connection to
`127.0.0.1:48077` succeeded. These checks establish that the reported process owned
a reachable dynamic loopback listener while the installed CLI reported the daemon
`ready`.

The installed preview server does not expose a dedicated HTTP health route documented
for this command surface. Probes to `/health` and to the older `/openai/status` route
both reached the listener but returned HTTP `404`. Consequently, the successful
`foundry server status` `ready` result is the health authority for this CLI version;
an HTTP `200` health endpoint is not claimed.

Command:

```powershell
foundry config show --output json
```

Exit code: `0`. Only non-secret endpoint/cache-related settings were selected from the
captured JSON:

```json
[
  {"key":"port","value":"auto","userSet":false},
  {"key":"cache-directory","value":"C:\\Users\\husoelrey\\.foundry\\cache\\models","userSet":false}
]
```

The automatic port setting agrees with the observed dynamic endpoint. The specific
port must not be hard-coded into application configuration.

### Model-cache configuration

Command:

```powershell
foundry cache location --output json
```

Exit code: `0`.

Exact output:

```json
{"path":"C:\\Users\\husoelrey\\.foundry\\cache\\models","userSet":false}
```

Post-start filesystem and daemon-log inspection found:

- Effective cache: `C:\Users\husoelrey\.foundry\cache\models`
- User override: no
- Locally cached models reported by the daemon: `0`
- Execution-provider directory: `C:\Users\husoelrey\.foundry\ep`
- Execution-provider files: `0`
- Model or execution-provider binary payloads: `0`
- External model root files: `0`
- Generated metadata index:
  `C:\Users\husoelrey\.foundry\cache\models\foundry.modelinfo.json`,
  `79,275` bytes, SHA-256
  `D06C700AA5CC62B481ADA4F606048900A050642A08D54D97C4C303C9397749A1`

The post-start evidence commands were:

```powershell
Get-ChildItem -LiteralPath 'C:\Users\husoelrey\.foundry' -Recurse -Force
Get-FileHash -LiteralPath 'C:\Users\husoelrey\.foundry\cache\models\foundry.modelinfo.json' -Algorithm SHA256
foundry server logs -n 50
```

Each command exited `0`. Daemon startup automatically contacted the Azure Foundry
catalog and wrote the JSON metadata index even though no catalog-list command was
issued. It also attempted automatic execution-provider registration, which failed
immediately because the generated request contained unknown provider names. The
daemon log then reported
`0` locally cached models; the execution-provider directory remained empty. This
means no model weights or execution-provider payloads were acquired, but daemon
startup is not network-silent and is not by itself proof of air-gapped readiness.

### Failures and minimum reproduction

The command documented by the current Microsoft page does not exist in the installed
CLI:

```powershell
foundry service status
```

Exit code: `2`.

Observed error:

```text
Unrecognized command or argument 'service'.
Hint: Run 'foundry --help' to see usage.
```

Minimum current-state reproduction:

```powershell
foundry server status --output json
```

Current result: daemon running with state `ready`. The endpoint and PID are dynamic,
so the JSON output must be read rather than copied from this record.

Fallback implication: daemon readiness does not make a Foundry deployment profile
available. No model or execution provider has been selected, downloaded, loaded, or
tested. Native Windows FastAPI remains the deployment fallback if later Docker bridge
verification is unsuitable.

## Inventory conclusion

The bounded runtime-readiness inventory and Foundry daemon-readiness prerequisite are
complete. Docker, Ollama, and the Foundry daemon are healthy on their verified local
surfaces, but no Foundry deployment profile exists and container-to-host connectivity
is still unverified.

The next bounded P1 step is to configure and verify runtime-supported external model
storage without acquiring models or running inference.
