Adversarially review the implementation spec at E:\openshot-mcp\docs\specs\2026-09-10-openshot-mcp-v1.md
for a Python MCP server that edits OpenShot 4.0 .osp project files. Reference material:
E:\claude_scratch\roomstack-trailer\openshot\osp_schema.json (real project schema excerpt),
E:\claude_scratch\roomstack-trailer\openshot\clip_probe.json (ffprobe of source clips),
E:\claude_scratch\roomstack-trailer\openshot\astra_answer.md (prior advice on .osp keys).
You may also consult the OpenShot sources on GitHub (openshot-qt v4.0.0 src/classes/project_data.py,
src/windows/models/files_model.py, timeline markers handling; libopenshot v1.0.0 src/Clip.cpp,
FFmpegReader.cpp) to check claims.

Find: (1) factual errors about the .osp format or OpenShot behavior that would make a saved project
fail to load or lose data; (2) missing tools or args that make the "agent places 15 clips on a beat
grid, human edits afterwards" flow impossible or clumsy; (3) design flaws (state model, locking,
atomic save, id generation, snapping math); (4) test-gate gaps; (5) anything over-scoped for v1.
Rank findings CRITICAL / MAJOR / MINOR, each with the spec line it targets and a concrete fix.
Under 800 words. No preamble.
