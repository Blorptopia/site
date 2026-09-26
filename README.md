# Blorptopia site
Curious about the content? See the [production instance](https://blorptopia.dev)
## Running this locally
```sh
# This starts a live-reloading local web server
python3 -m build live
```

## Scaffolding
```sh
python3 -m build gen post "Happy eyeballs"
python3 -m build gen project Gate
```

## Deploying
```sh
# This creates files in the "dist" folder for you to deploy to a static file host
python3 -m build dist
```
