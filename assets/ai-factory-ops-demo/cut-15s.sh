#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail
cd "$(dirname "$0")"

ffmpeg -y -loglevel error -i out/ai-factory-operations-agent.mp4 \
  -filter_complex '[0:v]setpts=(PTS-STARTPTS)*15/31,fps=60[v];[0:a]atempo=31/15[a]' \
  -map '[v]' -map '[a]' -t 15 -c:v libx264 -preset slow -crf 17 \
  -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k \
  -movflags +faststart out/ai-factory-operations-agent-15s.mp4
