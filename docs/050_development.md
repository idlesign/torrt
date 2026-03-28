# Development

For development we use [makeapp](https://pypi.org/project/makeapp/). Install:

```shell
$ uv tool install makeapp
```

After the repository is cloned, we use the following command in its directory:

```shell
# install utilities required
$ ma tools

# initialize virtual environment
$ ma up --tool
```

Now you are ready to develop.

Check code style before pull request:

```shell
$ ma style
```
