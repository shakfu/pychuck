# Chugins Directory

Place compiled ChucK plugins (chugins) here.

## What are Chugins?

Chugins are ChucK plugins that extend the language with new UGens,
functions, and capabilities. They are compiled native code (`.chug` files).

## Installing Chugins

1. Download or compile chugins from https://github.com/ccrma/chugins
2. Place `.chug` files in this directory
3. They will be automatically loaded when ChucK starts

## Popular Chugins

- **Faust** - Faust DSP language integration
- **Fluidsynth** - SoundFont synthesizer
- **Ladspa** - LADSPA plugin host
- **WarpBuf** - Time-stretching buffer

## Building Chugins

```bash
git clone https://github.com/ccrma/chugins.git
cd chugins
make linux  # or: make osx / make win
```

Copy the resulting `.chug` files to this directory.
