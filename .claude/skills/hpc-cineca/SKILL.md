---
name: hpc-cineca
description: Use when working with the CINECA HPC cluster (g100): SSH connection setup, repo sync via rsync, SLURM job submission and monitoring, and log analysis for BSB runs on HPC. Triggers on mentions of CINECA, g100, HPC, sbatch, slurm, or any task involving running BSB code remotely on compute nodes.
---

# HPC (CINECA) — BSB workflow

End-to-end procedures for getting BSB code from a dev's laptop onto CINECA's `g100` cluster, running it under SLURM, and analyzing logs.

## When to use this skill

- User wants to push local changes to HPC and run them
- User asks about a SLURM job, sbatch script, partition, squeue
- User wants to monitor or analyze HPC job logs
- User mentions CINECA / g100 / login.g100.cineca.it

## Bootstrap (do this FIRST, every session)

Read `~/.claude/cineca-personal.md`. It holds per-dev, per-machine details that get substituted into the procedures below (CINECA username, SSH binary path on this host, paths to the BSB checkout and venv on HPC, known_hosts location, etc.).

**If the personal file does not exist:** stop and ask the user to create it from this template, then continue:

```markdown
# CINECA personal setup (per-dev)

## Identity
- CINECA username: <your-cineca-username>
- Provisioner login email (step 1): <your-email-for-step-1>
- Login host: login.g100.cineca.it
- Full ssh target: <your-cineca-username>@login.g100.cineca.it

## Step 1 — cert refresh (every ~24h, interactive)
Uses the **smallstep** CLI (`step`), not OpenSSH. Run from <your-shell>; opens a browser; agent can launch the command (PowerShell has `step` on PATH) and hand off the browser portion to you:
    step ssh login '<your-email-for-step-1>' --provisioner cineca-hpc

⚠️ Do not drop the `step` prefix. A bare `ssh login ...` resolves to OpenSSH treating `login` as a hostname, which fails with `Connection refused`.

## Step 2 — SSH probe
    ssh -o BatchMode=yes -o ConnectTimeout=10 <your-cineca-username>@login.g100.cineca.it "<cmd>"

If host-key fingerprint mismatch, strip cineca entries from:
    <path-to-your-known_hosts-file>
Then retry. Allowed without asking.

## Machine quirks (fill in if you have any)
- SSH binary path (if non-default): <e.g. /c/Windows/System32/OpenSSH/ssh.exe>
- Shell-specific quoting traps to remember:

## HPC environment
- Editable BSB checkout on HPC (rsync target): <e.g. ~/libs/bsb>
- Python venv on HPC (activate before any work): <e.g. ~/libs/venv>
- Logs dir: ~/logs/ (relative to ~ at sbatch submission time)
- Production sbatch reference: <path to your sbatch script>

## SLURM accounts available to me
- Primary: <e.g. ERI2_E2_PAVIA>
- Alts: <list>
```

**Auto-discovery hint** when the dev says "I've already set up the venv but I don't know the paths": activate any candidate venv on HPC, run `pip show bsb-core`. `Editable project location` reveals the checkout; `Location` reveals the venv site-packages (strip `/lib/python*/site-packages` for venv root).

## Rules of engagement

- **Read-only / exploratory** commands on HPC (`sinfo`, `squeue`, `sacct`, `scontrol show`, `cat`, `ls`, `git status/log/diff`, `pip show`, `module list/avail`): run freely.
- **Mutations** (writes, `sbatch`, `srun`, `salloc`, `scancel`, `module load`, `pip install`, edits to remote files, etc.): sketch first, wait for user approval. Each new approval is for that specific action; not durable.
- **Cert refresh (step 1)**: agent launches `step ssh login ...` (the smallstep CLI, available on PowerShell PATH); only the browser portion is handed to the user. Never use a bare `ssh login ...` — that's OpenSSH and fails.
- **Known_hosts cineca entries**: safe to remove unilaterally on fingerprint mismatch (cineca rotates host keys periodically).
- **Smoke signal**: every sync increments `[RSYNC-BUILD] N` in the imported `bsb` module. Every job log MUST print this; if it doesn't, the wrong build is running.

## Parameters

Filled in from the personal file:

| Placeholder | Meaning |
|---|---|
| `<CINECA_USER>` | The dev's CINECA username (used in `user@host`) |
| `<PROVISIONER_EMAIL>` | The email for the step-1 cert provisioner |
| `<SSH_BIN>` | Path to the ssh binary that has the cineca cert (host-specific) |
| `<KNOWN_HOSTS>` | Path to known_hosts file containing cineca entries |
| `<BSB_CHECKOUT>` | rsync target on HPC; matches editable-install location |
| `<VENV_PATH>` | Python venv on HPC; sourced before every job |
| `<LOCAL_REPO>` | Path to the local repo from the agent's POV (e.g. `/home/<user>/git/bsb`) |
| `<ACCOUNT>` | SLURM account (e.g. `ERI2_E2_PAVIA`) |

---

## Connection

### Step 1 — cert refresh (interactive, every ~24h)

Detection: probe with step 2 (`BatchMode=yes`). On auth failure, redo step 1.

The agent can launch the `step` command itself; only the browser login needs the user. Run:

```
step ssh login '<PROVISIONER_EMAIL>' --provisioner cineca-hpc
```

Then prompt the user to complete the browser login: "Browser window should have opened — complete the login, then say 'ready'."

⚠️ The `step` prefix is mandatory — `step` is the smallstep CLI. Without it, PowerShell's bare `ssh` is OpenSSH and treats `login` as a hostname, failing with `Connection refused`.

### Step 2 — SSH probe

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 <CINECA_USER>@login.g100.cineca.it "<cmd>"
```

- `BatchMode=yes` fails fast instead of hanging on a prompt.
- Login nodes round-robin (`login01`, `login02`, etc.) — hostname differs between sessions.

### Known_hosts cleanup (allowed unilaterally)

On `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` or `Offending key in <KNOWN_HOSTS>:N`:

```bash
ssh-keygen -R login.g100.cineca.it
ssh-keygen -R g100.cineca.it    # may not exist, harmless
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new <CINECA_USER>@login.g100.cineca.it "<cmd>"
```

`StrictHostKeyChecking=accept-new` auto-registers the new key on the next call. Subsequent calls work normally without the flag. (Cineca rotates host keys; this is expected, not an attack.)

---

## Ad-hoc commands on compute nodes

For "run X on a compute node now and show me the output":

```bash
ssh ... '<CINECA_USER>@login.g100.cineca.it' \
  "srun -A <ACCOUNT> -p g100_usr_dbg --time=00:01:00 --ntasks=1 <cmd>"
```

- `srun` is synchronous; output streams back. No log file, no cleanup.
- `g100_usr_dbg` is the right partition for one-offs (20 nodes, default 30 min, no prod-quota burn).
- **No `salloc` needed** — standalone `srun` creates an allocation implicitly.

---

## Sync to HPC

**One atomic operation, three inseparable sub-steps.** Skipping any sub-step leaves the tree in a half-broken state. Always do all three.

### Sub-step 1 — rsync

```bash
rsync -avz --delete \
  --filter=':- .gitignore' \
  --exclude='.git/' --exclude='.claude/' --exclude='.patches/' --exclude='.rsync-build' \
  -e "<SSH_BIN>" \
  <LOCAL_REPO>/ \
  <CINECA_USER>@login.g100.cineca.it:<BSB_CHECKOUT>/
```

- `--filter=':- .gitignore'` honors the project's gitignore — handles IDE configs, build artifacts, hdf5/pkl/etc. automatically.
- Explicit excludes for what gitignore doesn't manage: `.git/` (HPC has its own git state), `.claude/` (per-dev tooling, local-only), `.patches/` (HPC-only patches; protected from `--delete`), `.rsync-build` (build counter).
- Trailing slash on source = "contents of"; without it, rsync nests one level deeper.
- `--delete` keeps HPC as a true mirror. Without it, stale files accumulate.

### Sub-step 2 — apply HPC-only patches

```bash
ssh ... "<CINECA_USER>@login.g100.cineca.it" "cd <BSB_CHECKOUT> && \
  shopt -s nullglob && \
  for p in .patches/*.patch; do \
    git apply --check \"\$p\" || { echo \"PATCH FAILED (dry): \$p\"; exit 1; }; \
    git apply \"\$p\" && echo \"Applied: \$p\"; \
  done"
```

- `.patches/` lives only on HPC (gitignored locally, `--exclude`d by rsync). Contains workarounds for HPC-specific constraints (e.g. no-internet on compute nodes).
- `git apply --check` first — never half-apply on drift. Stop on dry-failure and surface to the user.
- Patches are dev-managed: when one breaks against upstream drift, surface it, do not silently skip.

### Sub-step 3 — smoke signal + counter increment

```bash
ssh ... "<CINECA_USER>@login.g100.cineca.it" "cd <BSB_CHECKOUT> && \
  PREV=\$(cat .rsync-build 2>/dev/null || echo 0) && \
  NEXT=\$((PREV + 1)) && echo \$NEXT > .rsync-build && \
  INIT=packages/bsb-core/bsb/__init__.py && \
  sed -i '/^print(\"\\[RSYNC-BUILD\\]/d' \"\$INIT\" && \
  sed -i \"1i print(\\\"[RSYNC-BUILD] \$NEXT\\\", flush=True)\" \"\$INIT\" && \
  echo \"Synced. Build: \$NEXT\""
```

- Strip-then-insert = idempotent (re-running doesn't accumulate prints).
- Counter persists across syncs in `.rsync-build` (rsync-excluded).
- Every job that imports `bsb` will now print `[RSYNC-BUILD] N` once per rank — proof the right sync is running on the compute nodes.

### Verify (optional, run on first sync or after suspicious diffs)

```bash
ssh ... "srun -A <ACCOUNT> -p g100_usr_dbg --time=00:01:00 --ntasks=1 \
  <VENV_PATH>/bin/python -c 'import bsb'"
```

Should print `[RSYNC-BUILD] <NEXT>`. Skip on routine syncs.

### Failure handling

- `rsync` non-zero → stop, surface error.
- Patch dry-check fail → stop before applying any patch; show which one and why.
- `sed` fail → counter wasn't incremented, so next job log will still show prior build until next clean sync. Surface the error.

---

## Submitting sbatch jobs

**Submit from `$SCRATCH`, never from `$HOME`.** The submission cwd is what SLURM uses to resolve relative paths in the sbatch (`--output=logs/...`) AND what the job's process inherits as cwd (so relative paths inside the workload — config file references, `./morphologies/...` etc. — resolve against it). On g100, the canonical run-dir layout lives under `$SCRATCH` (`/g100_scratch/userexternal/<CINECA_USER>/`): configs, a `logs/` dir, and symlinks for `morphologies/` → the package source, `data/` → home-side data, etc. Running from `~` resolves relative paths against `$HOME`, which usually does NOT have these subdirs — jobs boot and then fail with `Couldn't find file:///g100/home/.../morphologies/...`.

Use a heredoc to avoid leaving script files on the remote:

```bash
ssh ... "<CINECA_USER>@login.g100.cineca.it" @'
cd $SCRATCH           # ALWAYS — relative paths in sbatch + config resolve here
sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=<name>
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=g100_usr_dbg  # or g100_usr_prod for real runs
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=<N>
#SBATCH --mem=0                   # use full node memory; only valid for full-node jobs
#SBATCH --output=logs/<name>_%j.log
#SBATCH --error=logs/<name>_%j.log   # merge stderr → same file

# Compute nodes don't inherit login-shell modules — always load them in the script.
module purge
module load profile/base cintools
module load python/3.11.7--gcc--10.2.0
module load zlib/1.2.11--gcc--10.2.0
module load gsl/2.7--gcc--10.2.0
module load openmpi/4.1.1--gcc--10.2.0-pmi-cuda-11.5.0
module load cmake/3.21.4
module load boost/1.77.0--openmpi--4.1.1--gcc--10.2.0-pmi
module load gcc/10.2.0
module load hdf5/1.10.7--openmpi--4.1.1--gcc--10.2.0-pmi-cxx
module load libtool/2.4.6--gcc--10.2.0-zxi

source <VENV_PATH>/bin/activate
source <VENV_PATH>/bin/nest_vars.sh   # only if nest is involved

srun <command>
EOF
'@
```

The `sbatch` call prints `Submitted batch job <ID>` — capture from stdout.

Conventions to follow:
- Logs land in `logs/<name>_%j.log` relative to submission cwd (usually `~`).
- `--mem=0` uses full node memory; only use when `--ntasks` = node CPU count.
- `srun` is the inner launcher even inside the sbatch — handles MPI rank wiring.

---

## Monitoring

### Snapshot queries (read-only, free to run)

- `squeue --me` — your current queue (state, runtime, nodelist).
- `scontrol show job <id>` — full state of one job (start/end, partition, account, nodelist, request).
- `sacct -j <id> --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS,ReqMem,Partition,DerivedExitCode` — post-mortem accounting.

### Live log tail (Monitor tool)

For watching a long-running job's log in real time:

```
Monitor: <SSH_BIN> -o BatchMode=yes <CINECA_USER>@login.g100.cineca.it \
  'timeout <Ns> tail -F -n +1 ~/logs/<name>_<jobid>.log 2>/dev/null | \
   grep --line-buffered -E "<TAG>|Traceback|[Ee]rror|FAILED|slurmstepd|CANCELLED|Killed|OOM|PMI|MPI_Init|exit code|return code"'
```

- `tail -F` (capital F) retries when the file doesn't exist yet — safe to start before job allocates.
- `--line-buffered` on grep is **mandatory** — without it, grep buffers in chunks and events arrive in bursts instead of streaming.
- Wrap with `timeout <Ns>` on the remote so the tail self-terminates if the job hangs or the session dies.
- The filter MUST include both success-progress lines (`<TAG>`) AND failure signatures. **Silence ≠ success** (Monitor docs) — if the filter only catches "happy path" lines, a crash will leave the monitor mute and look identical to "still running".

### Volume gotcha

The Monitor tool auto-stops monitors that produce too many notifications. A debug-trace run can emit thousands of `[BSB-TRACE` lines per rank. If your filter is too broad, important post-init failure messages (PMI errors, tracebacks) may be silently dropped after the throttle kicks in.

For verbose-trace jobs, prefer a narrow filter for live monitoring (just `[RSYNC-BUILD]`, banners, and failure signatures) and **fetch the full log post-mortem** for trace analysis:

```bash
ssh ... "tail -100 ~/logs/<name>_<jobid>.log; \
        grep -vE '^\\[BSB-TRACE' ~/logs/<name>_<jobid>.log | tail -50"
```

---

## Python / venv bootstrap (greenfield, one-time per new dev)

When a dev has no `<VENV_PATH>` or `<BSB_CHECKOUT>` yet:

```bash
ssh <CINECA_USER>@login.g100.cineca.it
# 1. Load the full bsb module stack (default python is loaded system-wide,
#    but the rest isn't — required for building mpi4py / h5py / etc.)
module purge
module load profile/base cintools \
            python/3.11.7--gcc--10.2.0 zlib/1.2.11--gcc--10.2.0 \
            gsl/2.7--gcc--10.2.0 openmpi/4.1.1--gcc--10.2.0-pmi-cuda-11.5.0 \
            cmake/3.21.4 boost/1.77.0--openmpi--4.1.1--gcc--10.2.0-pmi \
            gcc/10.2.0 hdf5/1.10.7--openmpi--4.1.1--gcc--10.2.0-pmi-cxx \
            libtool/2.4.6--gcc--10.2.0-zxi

# 2. Create venv and activate
python -m venv <VENV_PATH>          # e.g. ~/libs/venv
source <VENV_PATH>/bin/activate
pip install --upgrade pip

# 3. Sync local repo to <BSB_CHECKOUT> (use the rsync procedure above)

# 4. Editably install all bsb packages + sub-projects
for pkg in <BSB_CHECKOUT>/packages/*; do pip install -e "$pkg"; done
for pkg in <BSB_CHECKOUT>/libs/*; do
  [ -f "$pkg/pyproject.toml" ] && pip install -e "$pkg"
done

# 5. Record <VENV_PATH> and <BSB_CHECKOUT> in personal file
```

For an already-bootstrapped dev (the common case): sync = rsync + smoke-signal patch only; editable install picks up source changes automatically.

---

## SLURM reference

### Accounts & QOS

| Account | Notes |
|---|---|
| `ERI2_E2_PAVIA` | Primary project account (matches `$WORK=/g100_work/ERI2_E2_PAVIA`) |

QOS (within accounts):
- `normal` — default, no special limits
- `g100_qos_bprod` — big runs, max 64 nodes
- `g100_qos_lprod` — long runs, max 4 days wall

### Partition cheat sheet

| Partition | MaxTime | Use case | Notes |
|---|---|---|---|
| `g100_usr_dbg` | UNLIMITED (QOS-bounded) | Quick tests, ad-hoc | Default 30 min. 20 nodes, 48 CPUs each. Open to all accounts. Default `mem-per-cpu=7800M`. |
| `g100_usr_interactive` | 8 h, max 2 nodes/job | Interactive work, GPU debugging | 2 GPUs/node. Denies `g100_qos_bprod`. |
| `g100_usr_prod` | 24 h | Production runs | Full nodes (48 CPUs). |
| `g100_usr_smem` / `bmem` / `pmem` | 24 h | small / big / preemptable memory variants | |

### Useful env vars on HPC

After login shell:
- `$HOME=/g100/home/userexternal/<CINECA_USER>`
- `$WORK=/g100_work/<ACCOUNT>` (project area, shared with team)
- `$SCRATCH=/g100_scratch/userexternal/<CINECA_USER>`
- `$TMPDIR=/scratch_local` (node-local, ephemeral)

### MPI types available on cineca slurm

`srun --mpi=list` → `none`, `cray_shasta`, `pmi2`. **No `pmix`.** Defaults to `pmi2`.

---

## Known issues

### MPI_Init / PMI2 failure under srun (open, 2026-05-15)

Symptom from `bsb compile ...` under `srun`:
```
PMI2_Init failed to intialize.  Return code: 14
The application appears to have been direct launched using "srun",
but OMPI was not built with SLURM's PMI support and therefore cannot execute.
```

Root cause: cineca's `openmpi/4.1.1--gcc--10.2.0-pmi-cuda-11.5.0` module is named `-pmi` but its runtime PMI integration with cineca's slurm is broken. `srun --mpi=pmi2` explicit behaves identically (same failure).

Investigated workarounds:
- `srun --mpi=pmix` — N/A; cineca slurm doesn't have pmix plugin.
- `mpirun -n N` — failed previously with MPI RMA errors (per dev memory; older logs gone).
- Alt `openmpi/4.1.1--gcc--10.2.0-cuda-11.5.0` (no `-pmi`) — has no PMI client, worse for `srun`.
- `openmpi/4.1.6--gcc--12.2.0` — newer; requires gcc-12 stack and venv rebuild. **Viable but multi-hour project.**
- Escalate to cineca admins to rebuild OMPI with `--with-pmi` — real fix, outside dev's control.

### Trace volume can throttle Monitor

A full `bsb compile` with line-level import traces emits ~100+ trace lines per rank × 48 ranks. The Monitor tool's per-line notification throttle can drop important post-init failure messages. For verbose-trace jobs, monitor with a narrow filter and inspect the full log post-mortem.

---

## Working notes vs this skill

This file (`SKILL.md`) is the committable, distilled procedure. `NOTES.md` in the same directory is a gitignored scratch pad for ongoing exploration — capture new findings there first; promote to `SKILL.md` once patterns stabilize.
