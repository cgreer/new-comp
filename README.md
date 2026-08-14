
# Instructions

1. Install maccy (for clipboard history)

# Clipboard File

Run this in a tmuxp process:  

```while true; do ./dump-maccy-text.sh 100 ~/Dropbox/notes/clipboard_history.txt; sleep 10s; done```

# Keyboard stuff

Run these to make keyrepeat fast:  

```defaults write -g InitialKeyRepeat -int 12 # normal minimum is 15 (225 ms)```  
```defaults write -g KeyRepeat -int 1 # normal minimum is 2 (30 ms)```  

Use this for page up/down custom mod:

https://ke-complex-modifications.pqrs.org/

Install karabiner?



