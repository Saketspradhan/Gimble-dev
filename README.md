# Gimble.dev

Gimble is a cross-platform CLI for robotics debugging and observability on macOS and Linux.

## Install (Latest Release, Recommended)

Use this for first-time install and upgrades. It always resolves the newest GitHub release tag at install time (no hardcoded version in the command).

```bash
curl -fsSL https://raw.githubusercontent.com/Saketspradhan/Gimble-dev/main/scripts/install_latest.sh | bash
```

Verify:

```bash
gimble --version
```

## Package Manager Installs

### macOS (Homebrew tap)

```bash
brew tap saketspradhan/gimble https://github.com/Saketspradhan/Gimble-dev
brew install gimble
```

### Linux (APT)

One-time repository setup:

```bash
curl -fsSL https://raw.githubusercontent.com/Saketspradhan/Gimble-dev/gh-pages/gimble-archive-keyring.gpg \
  | sudo tee /usr/share/keyrings/gimble-archive-keyring.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/gimble-archive-keyring.gpg] https://saketspradhan.github.io/Gimble-dev stable main" \
  | sudo tee /etc/apt/sources.list.d/gimble.list >/dev/null
```

Install:

```bash
sudo apt update
sudo apt install gimble
```

## First Run

```bash
gimble
```

On first launch, Gimble runs an interactive setup wizard and stores local config/secrets under:

- macOS: `~/Library/Application Support/gimble/`
- Linux: `~/.config/gimble/`

## Session Commands

Inside a Gimble session, use:

- `gim chat` start chat server + public link
- `gim disconnect` stop chat/tunnel and ingestion, stay in Gimble session
- `gim exit` stop chat/tunnel (fail-safe) and exit Gimble session

## Chat Models

Default provider/model:

- Groq: `openai/gpt-oss-120b`

Available in UI:

- Groq: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `openai/gpt-oss-safeguard-20b`, `qwen/qwen3-32b`, `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`
- OpenAI: `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4.1-nano`
- `GPT-Q 4K` is shown as experimental placeholder (non-selectable)

## Public Chat Tunnel

`gim chat` can expose your local session as:

`https://chat.gimble.dev/<username>/<session_id>`

Broker/worker code is in:

- `infra/chat-broker/`

## Updating Gimble

Always install latest release tag:

```bash
curl -fsSL https://raw.githubusercontent.com/Saketspradhan/Gimble-dev/main/scripts/install_latest.sh | bash
```


## Maintainer Automation

On each `v*` tag push, GitHub Actions now auto-updates `Formula/gimble.rb` to that tag + tarball SHA256:

- workflow: `.github/workflows/update-homebrew-formula.yml`
- helper script: `scripts/update-homebrew-formula.sh`

This keeps Homebrew installs aligned with the newest release without manual formula edits.

## Remove Gimble Completely

```bash
brew uninstall --zap --force gimble || true
brew untap saketspradhan/gimble || true
rm -rf "$HOME/Library/Application Support/gimble" "$HOME/.config/gimble" "$HOME/.cache/gimble" "$HOME/.local/share/gimble" "$HOME/.gimble"
```

## Build From Source

```bash
make build
```

Linux/macOS release artifacts:

```bash
make build-linux
make build-macos
```

## License

See `LICENSE`.
