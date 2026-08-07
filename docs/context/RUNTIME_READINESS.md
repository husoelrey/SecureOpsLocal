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
