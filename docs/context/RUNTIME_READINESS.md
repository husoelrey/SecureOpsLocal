# SecureOps Local — Runtime Readiness

Last verified: **2026-08-07**

This file records read-only readiness evidence for the local runtimes used by
SecureOps Local. Installation, upgrade, model acquisition, cache population, and
inference are outside this inventory task.

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
process and loopback API are healthy. The effective default model cache exists but is
empty; this inventory did not list models through the API, acquire artifacts, or run
inference.

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

- `ollama.exe` process ID: `29060`
- `ollama app.exe` process ID: `3980`
- Listener: `127.0.0.1:11434`, owned by process `29060`
- Local API base URL: `http://127.0.0.1:11434/api`
- Version response: `{"version":"0.32.6"}`

The matching CLI and API versions plus the loopback listener verify local service
health. Process IDs are observations from this run and are expected to change after a
restart.

### Model-cache configuration

Commands:

```powershell
[Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'Process')
[Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'User')
[Environment]::GetEnvironmentVariable('OLLAMA_MODELS', 'Machine')
Get-ChildItem -LiteralPath 'C:\Users\husoelrey\.ollama\models' -Recurse -Force -File
```

Observed state:

- `OLLAMA_MODELS` was unset at process, user, and machine scopes.
- Effective documented Windows default: `C:\Users\husoelrey\.ollama\models`
- Cache directory exists: yes
- Cached files: `0`
- Cached bytes: `0`

No file was created, moved, deleted, or downloaded. The project-managed external
model root at `C:\Users\husoelrey\Documents\docs\AI_models` is not yet configured as
Ollama's effective cache; changing that configuration is later P1 work and requires
runtime-supported-path verification first.

### Failure and fallback implications

No Ollama readiness command failed. The service binds only to Windows loopback in the
observed state, which is safe for local use but does not prove reachability from a
Docker container. `host.docker.internal:11434` connectivity and any required trusted
host-binding change remain a later, explicit P1 test. Native Windows FastAPI can use
the verified loopback endpoint if container-to-host access is unavailable.
