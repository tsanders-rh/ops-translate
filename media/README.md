# Demo Video Production Guide

This guide explains how to create the ops-translate demo video using VHS (Video Handwriting Synthesizer).

**Demo Focus:** Multi-source merge workflow combining dev provisioning, prod provisioning, and approval workflow into a unified automation.

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

### 3. Mock LLM Provider (No API Key Needed)

The tape is configured to use the mock LLM provider, so no API key is required. The demo will work completely offline.

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

**Duration:** ~4-5 minutes (as scripted)

**What's demonstrated:**
- Import 3 sources (dev-provision.ps1, prod-provision.ps1, approval.workflow.xml)
- Static analysis without AI
- Intent extraction (creates 3 intent files)
- Gap analysis review
- Merge 3 intent files → 1 unified workflow
- Dry-run validation
- Generate KubeVirt + Ansible artifacts

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

## Demo Workflow

The tape follows this sequence:

1. **Initialize & Import** - Create workspace and import 3 sources
2. **Summarize** - Static analysis without AI
3. **Extract Intent** - AI extraction creating 3 intent files
4. **Gap Analysis** - Review translatability classifications
5. **Merge Intent** - Combine 3 files into unified workflow
6. **Dry-Run Validation** - Validate merged intent
7. **Generate Artifacts** - Create KubeVirt and Ansible outputs

Each scene is clearly labeled in the terminal output.

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
