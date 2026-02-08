# Demo Video Production Guide

This guide explains how to create the ops-translate demo video using VHS (Video Handwriting Synthesizer).

## Directory Structure

```
media/
├── README.md                   # This file
├── ops-translate-demo.tape     # VHS recording script
└── ops-translate-demo.mp4      # Generated video (after running VHS)
```

## Prerequisites

### 1. Install VHS

```bash
# macOS
brew install vhs

# Linux
# Download from https://github.com/charmbracelet/vhs/releases
```

### 2. Install ops-translate

```bash
# From the repository root
pip install -e .

# Verify it's on PATH
which ops-translate
```

### 3. Optional: OpenShift Cluster Access

For the final `oc apply` steps to succeed:
- CRC running locally, or
- Connection to an OpenShift cluster

If you don't have access, the demo will still work (those commands use `|| true` to prevent failures).

## Recording the Demo

### Run the VHS Tape

From the repository root:

```bash
vhs media/ops-translate-demo.tape
```

This will:
1. Execute all commands in the tape file
2. Record the terminal output
3. Generate `media/ops-translate-demo.mp4`

**Duration:** ~5 minutes (as scripted)

### Customizing the Recording

Edit `media/ops-translate-demo.tape` to adjust:

- **Timing:** Change `Sleep XXXms` values to match your narration
- **Appearance:** Modify `Set Theme`, `Set FontSize`, `Set Width/Height`
- **Content:** Add/remove commands as needed

Available themes:
- `Dracula` (default, high contrast)
- `Nord`
- `Monokai`
- `Catppuccin`

### Testing Individual Sections

You can extract portions of the tape into separate files for testing:

```bash
# Example: test just the import section
vhs test-import.tape
```

## Interview Answers

The tape includes pre-filled answers for the `ops-translate interview` command:

```tape
Type "manual"         # Approval handling
Enter
Type "integration"    # REST/API purpose
Enter
Type "map-to-ovn-kubernetes"  # Network model
Enter
Type "platform-team"  # Ownership
Enter
```

**Adjust these** to match your actual interview prompts if they change.

## Post-Production

### Add Narration

The VHS output is a clean MP4 with no audio. To add narration:

1. Record your narration separately (following the script in `DEMO.md`)
2. Use a video editor to overlay the audio:
   ```bash
   # Using ffmpeg
   ffmpeg -i media/ops-translate-demo.mp4 -i media/narration.m4a \
          -c:v copy -c:a aac -shortest \
          media/ops-translate-demo-final.mp4
   ```

### Add UI Recording (Step 7)

For the OpenShift Console portion:
1. Record separately using QuickTime or OBS
2. Combine the videos:
   ```bash
   # Concatenate videos
   ffmpeg -i media/ops-translate-demo.mp4 -i media/openshift-console.mp4 \
          -filter_complex "[0:v][1:v]concat=n=2:v=1[outv]" \
          -map "[outv]" media/ops-translate-complete.mp4
   ```

## Troubleshooting

### VHS Not Found
```bash
# Check installation
vhs --version

# Reinstall if needed
brew reinstall vhs
```

### Commands Failing
- Ensure `ops-translate` is installed and on PATH
- Check that example files exist in `examples/powercli/` and `examples/vrealize/`
- Run commands manually first to verify they work

### Timing Issues
- If commands finish too quickly, increase `Sleep` values
- If they're too slow, decrease `Sleep` values
- VHS records in real-time, so adjust for your machine's speed

### File Size Too Large
```bash
# Compress the output
ffmpeg -i media/ops-translate-demo.mp4 \
       -vcodec libx264 -crf 28 \
       media/ops-translate-demo-compressed.mp4
```

## CI/CD Integration

You can regenerate the video automatically:

```yaml
# .github/workflows/demo-video.yml
name: Regenerate Demo Video
on:
  push:
    paths:
      - 'media/ops-translate-demo.tape'
      - 'examples/**'

jobs:
  record:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: charmbracelet/vhs-action@v2
        with:
          path: media/ops-translate-demo.tape
      - uses: actions/upload-artifact@v4
        with:
          name: demo-video
          path: media/ops-translate-demo.mp4
```

## Why VHS?

✅ **Deterministic:** Same output every time
✅ **Version controlled:** Tape file lives in git
✅ **Maintainable:** Update script, not re-record
✅ **Professional:** Clean, consistent terminal output
✅ **CI-friendly:** Automate regeneration

Perfect for ops-translate's "trust-first" positioning.
