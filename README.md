# Blorptopia site
Curious about the content? See the [production instance](https://blorptopia.dev)
## Running this locally
```sh
# This needs to be called every time you make a change
python3 -m build dist
# This server can be left running
(cd build/dist && python3 -m http.server 8000)
```
