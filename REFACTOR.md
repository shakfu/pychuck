Refactor the tui code to allow for different views: 

(1) a chuck livecoding  editor 

(with syntax highlighting) which does not behave like a repl. (see demo0.py for a possible example of this layout but not of the colors) 

It should be possible to spork the existing buffer of code or file under editing and replace the existing shred with the same id. This becomes a livecoding editor. Versions of the code or file in each tab are saved in ~/.pychuck/editor; and

(2) an improved version of the current (livecoding) repl.

There should be some common behaviour across the two views:

- chuck code is syntax highlighted by the ChuckLexer
- ctrl-q exits the application
- F1 opens the help window
- F2 shows a table of current shreds sorted by id, name, time 
created since audio started
- F3 shows the log which can contain chuck log output
etc..

The code should restructered as follows:

```sh
pychuck
  __init__.py
  __main__.py
  _pychuck.so
  chuck_lang.py
  cli.py
  tui/
    __init__.py
    chuck_lexer.py
    commands.py
    common.py
    editor.py
    parser.py
    paths.py
    repl.py
    session.py
```


The cli should be have the following api:

pychuck [<file>, ...]
  should have a subset of chuck executable options in argparse-style))

```sh
usage: chuck --[options|commands] [+-=^] file1 file2 ...

    [options] = halt|loop|audio|silent|dump|nodump|about|probe
                channels:<N>|out:<N>|in:<N>|dac:<N>|adc:<N>|driver:<name>
                srate:<N>|bufsize:<N>|bufnum:<N>|shell|empty
                remote:<hostname>|port:<N>|verbose:<N>|level:<N>
                callback|deprecate:{stop|warn|ignore}|chugin-probe
                chugin-load:{on|off}|chugin-path:<path>|chugin:<name>
                color:{on|off}|pid-file:<path>|cmd-listener:{on|off}
                query|query:<name>
   [commands] = add|replace|remove|remove.all|status|time|
                clear.vm|reset.id|abort.shred|exit
       [+-=^] = shortcuts for add, remove, replace, status
```

and also the following:

`pychuck edit [<file>, ..]`
  start the editor (if no paths are given)
  start editor and load file(s) if paths are given

`pychuck repl [<file>, ..]`
  start the repl (if no paths are given)
  start repl and load file(s) if paths are given

  repl should be able to access the chuck executables commands (above)

