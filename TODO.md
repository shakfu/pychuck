# TODO

- [ ] enable advanced chugins {faust, warpbuf, fluidsynth}
- [ ] evaluate and bundle additional chugins from https://github.com/shakfu/my-chugins:
  - **CLAP** -- load CLAP (CLever Audio Plugin) format plugins as ChucK UGens. Requires CLAP SDK.
  - **PdPatch** -- embed Pure Data patches as ChucK UGens. Requires libpd.
  - **VST3** -- load VST3 format plugins as ChucK UGens. Requires VST3 SDK.
  - Note: AbletonLink and AudioUnit from that repo are already bundled.

---

## Future Enhancements

### Tooling

- [ ] **LSP server for IDE integration**
  - Language Server Protocol implementation for ChucK
  - Would enable VS Code, Neovim, etc. integration
  - Features: syntax errors, completions, hover docs

### Documentation

- [ ] **Interactive tutorial**
  - Step-by-step livecoding introduction
  - Could be a guided REPL mode or web-based

- [ ] **Cookbook**
  - Common patterns and recipes
  - Examples: FM synthesis, drum machines, effects chains

- [ ] **Video documentation**
  - Screen recordings of livecoding sessions
  - Tutorial videos showing REPL/editor workflows
